"""
Module for syncing posts with Trello.

This module provides functionality to:
- Create and configure the SociClaw Trello board
- Create cards for generated posts
- Update card status
- Attach images to cards
"""

import hashlib
import logging
import os
import time
from datetime import datetime
from typing import List, Optional

try:
    from trello import TrelloClient
except ImportError:  # pragma: no cover - handled during initialization
    TrelloClient = None

from .content_generator import GeneratedPost

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrelloSync:
    """
    Sync SociClaw posts with Trello.
    """

    BOARD_NAME = "SociClaw Content Calendar"

    def __init__(
        self,
        api_key: Optional[str] = None,
        token: Optional[str] = None,
        board_id: Optional[str] = None,
        client: Optional[TrelloClient] = None,
        request_delay_seconds: Optional[float] = None,
    ) -> None:
        """
        Initialize TrelloSync.

        Args:
            api_key: Trello API key
            token: Trello API token
            board_id: Existing board ID (optional)
            client: Optional TrelloClient instance for testing/mocking
        """
        self.api_key = api_key or os.getenv("TRELLO_API_KEY")
        self.token = token or os.getenv("TRELLO_TOKEN")
        self.board_id = board_id or os.getenv("TRELLO_BOARD_ID")
        if request_delay_seconds is None:
            request_delay_seconds = float(os.getenv("SOCICLAW_TRELLO_DELAY_SECONDS", "0.2"))
        self.request_delay_seconds = max(0.0, float(request_delay_seconds))

        if not client and (not self.api_key or not self.token):
            raise ValueError("TRELLO_API_KEY and TRELLO_TOKEN must be provided")

        if client is not None:
            self.client = client
        else:
            if TrelloClient is None:
                raise ImportError("py-trello is required for Trello sync")
            self.client = TrelloClient(api_key=self.api_key, token=self.token)
        self.board = None

    def setup_board(self) -> None:
        """
        Ensure the SociClaw board and required lists exist.
        """
        if self.board_id:
            self.board = self.client.get_board(self.board_id)
            logger.info("Using existing Trello board")
        else:
            self.board = self._find_or_create_board(self.BOARD_NAME)

        self._ensure_lists()

    def create_card(self, post: GeneratedPost, list_name: str = "Backlog"):
        """
        Create a Trello card for a generated post.

        Args:
            post: GeneratedPost instance
            list_name: Target list name

        Returns:
            Created card object
        """
        if not self.board:
            self.setup_board()

        target_list = self._get_list_by_name(list_name)
        if not target_list:
            raise ValueError(f"List not found: {list_name}")

        title = self._summarize_title(post.text)
        post_id = self._build_post_identity(post)
        existing = self._find_card_by_identity(target_list, post_id)
        if existing:
            return existing

        due_date = self._build_due_date(post)
        description = f"{post.text}\n\n[SociClaw-ID:{post_id}]"
        card = target_list.add_card(name=title, desc=description, due=due_date)
        self._throttle()

        label = self._get_or_create_label(post.category)
        if label:
            card.add_label(label)

        self._ensure_checklist(card)
        return card

    def update_card_status(self, card_id: str, list_name: str):
        """
        Move a card to a different list (status).
        """
        if not self.board:
            self.setup_board()

        target_list = self._get_list_by_name(list_name)
        if not target_list:
            raise ValueError(f"List not found: {list_name}")

        card = self.client.get_card(card_id)
        card.change_list(target_list.id)
        self._throttle()
        return card

    def attach_image(self, card_id: str, image_url: Optional[str] = None, image_path: Optional[str] = None) -> None:
        """
        Attach an image to a card.
        """
        card = self.client.get_card(card_id)
        if image_url:
            card.attach(name="image", url=image_url)
            self._throttle()
            return
        if image_path:
            with open(image_path, "rb") as handle:
                card.attach(name="image", file=handle)
            self._throttle()
            return
        raise ValueError("image_url or image_path is required")

    def _find_or_create_board(self, name: str):
        boards = self.client.list_boards()
        for board in boards:
            if board.name == name:
                logger.info("Found existing Trello board")
                return board
        logger.info("Creating Trello board")
        return self.client.add_board(name)

    def _ensure_lists(self) -> None:
        existing_lists = {lst.name: lst for lst in self.board.list_lists("open")}
        for name in self._required_list_names():
            if name not in existing_lists:
                self.board.add_list(name)

    def _required_list_names(self) -> List[str]:
        months = {
            "Q1 2026": ["January", "February", "March"],
            "Q2 2026": ["April", "May", "June"],
            "Q3 2026": ["July", "August", "September"],
            "Q4 2026": ["October", "November", "December"],
        }

        list_names = ["Backlog"]
        for quarter, quarter_months in months.items():
            for month in quarter_months:
                list_names.append(f"{quarter} - {month}")
        list_names.extend(["Review", "Scheduled", "Published"])
        return list_names

    def _get_list_by_name(self, name: str):
        lists = self.board.list_lists("open")
        for lst in lists:
            if lst.name == name:
                return lst
        return None

    def _get_or_create_label(self, name: str):
        labels = self.board.get_labels()
        for label in labels:
            if label.name == name:
                return label
        return self.board.add_label(name, "blue")

    def _summarize_title(self, text: str) -> str:
        if not text or not text.strip():
            return "Untitled Post"
        first_line = text.strip().splitlines()[0]
        return (first_line[:80] + "...") if len(first_line) > 80 else first_line

    def _build_due_date(self, post: GeneratedPost) -> Optional[datetime]:
        if not post.date or post.time is None:
            return None
        try:
            date_obj = datetime.fromisoformat(post.date)
            return date_obj.replace(hour=int(post.time), minute=0, second=0, microsecond=0)
        except Exception:
            return None

    def _ensure_checklist(self, card) -> None:
        checklist_name = "Approval"
        for checklist in card.get_checklists():
            if checklist.name == checklist_name:
                return

        checklist = card.add_checklist(checklist_name)
        for item in ["Review copy", "Approve image", "Schedule"]:
            checklist.add_checklist_item(item, checked=False)
            self._throttle()

    def _throttle(self) -> None:
        if self.request_delay_seconds > 0:
            time.sleep(self.request_delay_seconds)

    def _build_post_identity(self, post: GeneratedPost) -> str:
        base = "|".join(
            [
                str(post.date or ""),
                str(post.time or ""),
                str(post.category or ""),
                str(post.text or ""),
            ]
        )
        return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]

    def _find_card_by_identity(self, target_list, post_id: str):
        marker = f"[SociClaw-ID:{post_id}]"
        try:
            cards = target_list.list_cards()
        except Exception:
            return None
        for card in cards:
            desc = getattr(card, "description", "") or ""
            if marker in desc:
                return card
        return None
