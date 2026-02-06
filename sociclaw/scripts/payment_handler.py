"""
Module for handling USDC payments on Base via the SociClawPayments contract.

NOTE: This is optional/future. Current flow uses off-chain credits managed by the image provider.

This module provides functionality to:
- Connect to Base via RPC
- Read user credit balances
- Listen for payment events
- Consume credits after image generation
"""

import json
import logging
import os
import time
from typing import Optional, Any

try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
except ImportError:  # pragma: no cover - handled during initialization
    Web3 = None
    geth_poa_middleware = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


SOCICLAW_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "credits", "type": "uint256"},
        ],
        "name": "PaymentReceived",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "credits", "type": "uint256"},
        ],
        "name": "CreditsUsed",
        "type": "event",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "amount", "type": "uint256"}],
        "name": "deposit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getCredits",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "useCredit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


class PaymentHandler:
    """
    Handle USDC payments and credits using the SociClawPayments contract.
    """

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        contract_address: Optional[str] = None,
        private_key: Optional[str] = None,
        web3: Optional[Web3] = None,
        abi: Optional[Any] = None,
    ) -> None:
        """
        Initialize the PaymentHandler.

        Args:
            contract_address: SociClawPayments contract address
            private_key: Owner private key for credit consumption
            web3: Optional Web3 instance for testing/mocking
            abi: Optional contract ABI override
        """
        self.rpc_url = rpc_url or os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
        self.contract_address = contract_address or os.getenv("SOCICLAW_CONTRACT_ADDRESS")
        self.private_key = private_key or os.getenv("SOCICLAW_WALLET_PRIVATE_KEY")

        if not self.contract_address:
            raise ValueError("SOCICLAW_CONTRACT_ADDRESS must be provided")

        if web3 is not None:
            self.web3 = web3
        else:
            if Web3 is None:
                raise ImportError("web3 is required for payment handling")
            self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if geth_poa_middleware is not None:
                self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        self.contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(self.contract_address),
            abi=abi or SOCICLAW_ABI,
        )

        self.account = None
        if self.private_key:
            self.account = self.web3.eth.account.from_key(self.private_key)

        logger.info("PaymentHandler initialized")

    def get_credits(self, user_address: str) -> int:
        """
        Get credit balance for a user.
        """
        checksum = self.web3.to_checksum_address(user_address)
        return int(self.contract.functions.getCredits(checksum).call())

    def use_credit(self, user_address: str) -> str:
        """
        Consume one credit for a user.

        Returns:
            Transaction hash
        """
        if not self.account:
            raise ValueError("SOCICLAW_WALLET_PRIVATE_KEY is required to send transactions")

        checksum = self.web3.to_checksum_address(user_address)
        nonce = self.web3.eth.get_transaction_count(self.account.address)

        tx = self.contract.functions.useCredit(checksum).build_transaction(
            {
                "from": self.account.address,
                "nonce": nonce,
                "gas": 200000,
                "gasPrice": self.web3.eth.gas_price,
            }
        )

        signed = self.account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.transactionHash.hex()

    def get_deposit_address(self) -> str:
        """
        Return the contract address to receive deposits.
        """
        return self.contract_address

    def wait_for_payment(
        self,
        user_address: str,
        amount: float,
        timeout: int = 300,
        poll_interval: int = 5,
    ) -> dict:
        """
        Wait for a payment event from a specific user.

        Args:
            user_address: User wallet address
            amount: Expected amount in USDC (human units)
            timeout: Max seconds to wait
            poll_interval: Polling interval in seconds

        Returns:
            Event data dict
        """
        checksum = self.web3.to_checksum_address(user_address)
        target_amount = self._to_usdc_amount(amount)

        event_filter = self.contract.events.PaymentReceived.create_filter(
            fromBlock="latest",
            argument_filters={"user": checksum},
        )

        deadline = time.time() + timeout
        while time.time() < deadline:
            for event in event_filter.get_new_entries():
                event_amount = int(event["args"]["amount"])
                if event_amount >= target_amount:
                    return event
            time.sleep(poll_interval)

        raise TimeoutError("Payment not received within timeout")

    def _to_usdc_amount(self, amount: float) -> int:
        """
        Convert human USDC amount to integer with 6 decimals.
        """
        return int(amount * 1_000_000)
