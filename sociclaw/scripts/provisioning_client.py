"""
Provisioning client for SociClaw users (Internal).

This client handles user provisioning and API key creation.
The underlying provider details are abstracted away from user-facing code.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from .http_retry import request_with_retry
from .validators import validate_provider, validate_provider_user_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProvisionResult:
    provider: str
    provider_user_id: str
    api_key: Optional[str]
    wallet_address: Optional[str]
    raw: Dict[str, Any]


class ProvisioningClient:
    def __init__(
        self,
        *,
        openclaw_secret: str,
        url: Optional[str] = None,
        timeout_seconds: int = 30,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not openclaw_secret or not openclaw_secret.strip():
            raise ValueError("openclaw_secret is required")

        self.openclaw_secret = openclaw_secret.strip()
        self.url = ((url or "").strip() or os.getenv("SOCICLAW_PROVISION_UPSTREAM_URL", "").strip())
        if not self.url:
            raise ValueError("Provisioning URL is required (set --url or SOCICLAW_PROVISION_UPSTREAM_URL)")
        self.timeout_seconds = int(timeout_seconds)
        self.max_retries = int(os.getenv("SOCICLAW_HTTP_MAX_RETRIES", "3"))
        self.backoff_base_seconds = float(os.getenv("SOCICLAW_HTTP_BACKOFF_SECONDS", "0.5"))
        self.session = session or requests.Session()

    def provision(
        self,
        *,
        provider: str,
        provider_user_id: str,
        create_api_key: bool = True,
    ) -> ProvisionResult:
        provider = validate_provider(provider)
        provider_user_id = validate_provider_user_id(provider_user_id)

        payload = {
            "provider": provider,
            "provider_user_id": str(provider_user_id),
            "create_api_key": bool(create_api_key),
        }

        resp = request_with_retry(
            session=self.session,
            method="POST",
            url=self.url,
            headers={
                "x-openclaw-secret": self.openclaw_secret,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
            backoff_base_seconds=self.backoff_base_seconds,
        )
        resp.raise_for_status()
        data = resp.json()

        nested = data.get("data") if isinstance(data.get("data"), dict) else {}
        # Contract order:
        # 1) data.api_key
        # 2) api_key
        # 3) data.image_api_key
        # 4) image_api_key
        api_key = (
            nested.get("api_key")
            or data.get("api_key")
            or nested.get("image_api_key")
            or data.get("image_api_key")
        )
        if not api_key:
            for container in (data, nested):
                for k, v in container.items():
                    if k.endswith("_api_key") and v:
                        api_key = v
                        break
                if api_key:
                    break
        wallet_address = (
            data.get("wallet_address")
            or data.get("wallet")
            or (data.get("data") or {}).get("wallet_address")
            or (data.get("data") or {}).get("wallet")
        )

        return ProvisionResult(
            provider=provider,
            provider_user_id=str(provider_user_id),
            api_key=str(api_key) if api_key else None,
            wallet_address=str(wallet_address) if wallet_address else None,
            raw=data,
        )
