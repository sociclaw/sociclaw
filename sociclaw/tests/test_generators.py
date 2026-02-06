import asyncio
from datetime import datetime
from unittest.mock import MagicMock

from sociclaw.scripts.content_generator import ContentGenerator, GeneratedPost
from sociclaw.scripts.image_generator import ImageGenerator
from sociclaw.scripts.notion_sync import NotionSync
from sociclaw.scripts.payment_handler import PaymentHandler
from sociclaw.scripts.research import TrendResearcher
from sociclaw.scripts.scheduler import QuarterlyScheduler, PostPlan
from sociclaw.scripts.trello_sync import TrelloSync


class DummyTweet:
    def __init__(self, text, created_at, metrics, entities=None, referenced=None):
        self.id = 1
        self.text = text
        self.created_at = created_at
        self.public_metrics = metrics
        self.entities = entities or {}
        self.referenced_tweets = referenced or []


class DummyResponse:
    def __init__(self, data):
        self.data = data


class DummyClient:
    def search_recent_tweets(self, **kwargs):
        tweets = [
            DummyTweet(
                "Post about #Crypto",
                datetime.utcnow(),
                {"like_count": 10, "retweet_count": 2, "reply_count": 1},
                entities={"hashtags": [{"tag": "Crypto"}]},
            ),
            DummyTweet(
                "Thread reply",
                datetime.utcnow(),
                {"like_count": 5, "retweet_count": 1, "reply_count": 0},
                referenced=[{"type": "replied_to"}],
            ),
        ]
        return DummyResponse(tweets)


def test_trend_researcher():
    researcher = TrendResearcher(api_key="test", client=DummyClient())

    trend_data = asyncio.run(researcher.research_trends("crypto", days=1))

    assert "crypto" in [t.lower() for t in trend_data.topics] or trend_data.topics
    assert len(trend_data.sample_posts) == 2


def test_quarterly_scheduler():
    scheduler = QuarterlyScheduler()
    trend_data = MagicMock()
    trend_data.peak_hours = [13, 17, 21]
    trend_data.topics = ["Bitcoin", "Ethereum", "DeFi"]
    trend_data.hashtags = ["Crypto", "Web3", "Blockchain"]

    plans = scheduler.generate_quarterly_plan(trend_data)

    assert len(plans) == 180
    assert all(isinstance(plan, PostPlan) for plan in plans)


def test_content_generator():
    generator = ContentGenerator()
    plan = PostPlan(
        date=datetime.utcnow(),
        time=13,
        category="tips",
        topic="hardware wallet",
        hashtags=["Crypto", "Web3", "Security"],
    )

    post = generator.generate_post(plan)

    assert len(post.text) <= generator.MAX_TWEET_LENGTH
    assert post.image_prompt
    assert isinstance(post, GeneratedPost)


def test_image_generator(monkeypatch, tmp_path):
    class DummyPayment:
        def get_credits(self, user_address):
            return 1

        def use_credit(self, user_address):
            return None

    class DummyImageProviderClient:
        def __init__(self):
            self.called = False
            self.kwargs = None

        def generate_image(self, **kwargs):
            self.called = True
            self.kwargs = kwargs
            return "http://example.com/image.png"

    class DummyResponse:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            return None

    def dummy_get(url, timeout=30):
        return DummyResponse(b"fake-image-bytes")

    monkeypatch.setattr("sociclaw.scripts.image_generator.requests.get", dummy_get)

    provider = DummyImageProviderClient()
    generator = ImageGenerator(
        model="nano-banana",
        provider_client=provider,
        output_dir=tmp_path,
        payment_handler=DummyPayment(),
    )

    result = generator.generate_image("test prompt", "0xabc")

    assert provider.called is True
    assert provider.kwargs["model"] == "nano-banana"
    assert provider.kwargs["user_id"] == "0xabc"
    assert result.url == "http://example.com/image.png"
    assert result.local_path.exists()


def test_trello_sync(sample_generated_posts):
    client = MagicMock()
    board = MagicMock()
    list_obj = MagicMock()
    list_obj.name = "Backlog"
    card = MagicMock()
    list_obj.add_card.return_value = card

    board.list_lists.return_value = [list_obj]
    board.get_labels.return_value = []
    board.add_label.return_value = MagicMock()
    card.get_checklists.return_value = []
    card.add_checklist.return_value = MagicMock()

    client.get_board.return_value = board

    sync = TrelloSync(api_key="key", token="token", board_id="board", client=client)
    sync.setup_board()
    created = sync.create_card(sample_generated_posts[0])

    assert created == card
    list_obj.add_card.assert_called_once()


def test_notion_sync(sample_generated_posts):
    client = MagicMock()
    client.pages.create.return_value = {"id": "page"}

    sync = NotionSync(api_key="key", database_id="db", client=client)
    page = sync.create_page(sample_generated_posts[0])

    assert page["id"] == "page"
    client.pages.create.assert_called_once()


def test_payment_handler():
    class DummyReceipt:
        def __init__(self):
            self.transactionHash = b"\x12"

    class DummySigned:
        rawTransaction = b"\x00"

    class DummyAccount:
        address = "0xowner"

        def sign_transaction(self, tx):
            return DummySigned()

    class DummyEthAccount:
        def from_key(self, key):
            return DummyAccount()

    class DummyEventFilter:
        def __init__(self):
            self._called = False

        def get_new_entries(self):
            if self._called:
                return []
            self._called = True
            return [
                {
                    "args": {
                        "user": "0x123",
                        "amount": 1_000_000,
                        "credits": 6,
                    }
                }
            ]

    class DummyEvents:
        class PaymentReceived:
            @staticmethod
            def create_filter(fromBlock="latest", argument_filters=None):
                return DummyEventFilter()

    class DummyFunctions:
        def getCredits(self, user):
            class Call:
                def call(self):
                    return 5

            return Call()

        def useCredit(self, user):
            class Builder:
                def build_transaction(self, params):
                    return {"to": "0xcontract", "data": "0x"}

            return Builder()

    class DummyContract:
        functions = DummyFunctions()
        events = DummyEvents()

    class DummyEth:
        gas_price = 1
        account = DummyEthAccount()

        def contract(self, address, abi):
            return DummyContract()

        def get_transaction_count(self, address):
            return 0

        def send_raw_transaction(self, raw):
            return b"\x12"

        def wait_for_transaction_receipt(self, tx_hash):
            return DummyReceipt()

    class DummyMiddleware:
        def inject(self, *args, **kwargs):
            return None

    class DummyWeb3:
        eth = DummyEth()
        middleware_onion = DummyMiddleware()

        def to_checksum_address(self, address):
            return address

    handler = PaymentHandler(
        rpc_url="http://localhost",
        contract_address="0xcontract",
        private_key="0xabc",
        web3=DummyWeb3(),
    )

    assert handler.get_credits("0x123") == 5
    assert handler.use_credit("0x123") == "12"
    event = handler.wait_for_payment("0x123", 1, timeout=1, poll_interval=0)
    assert event["args"]["amount"] == 1_000_000
