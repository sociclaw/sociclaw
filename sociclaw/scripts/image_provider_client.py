"""
Image Provider API client (Internal).

This client handles image generation API calls.
The underlying provider details are abstracted away from user-facing code.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageJobResult:
    job_id: str
    status: str
    result_url: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class ImageProviderClient:
    def __init__(
        self,
        api_key: str,
        generate_url: Optional[str] = None,
        jobs_base_url: Optional[str] = None,
        timeout_seconds: int = 30,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("API key is required")

        base_url = (os.getenv("SOCICLAW_IMAGE_API_BASE_URL") or "").strip().rstrip("/")
        default_generate_url = (
            f"{base_url}/api/v1?path=generate"
            if base_url
            else ""
        )
        default_jobs_base_url = (
            f"{base_url}/api/v1/jobs/"
            if base_url
            else ""
        )

        self.api_key = api_key.strip()
        self.generate_url = (generate_url or default_generate_url).strip()
        self.jobs_base_url = (jobs_base_url or default_jobs_base_url).strip().rstrip("/")
        if not self.generate_url or not self.jobs_base_url:
            raise ValueError(
                "Image API URLs are required. Set SOCICLAW_IMAGE_API_BASE_URL or pass generate_url/jobs_base_url."
            )
        self.jobs_base_url += "/"
        self.timeout_seconds = int(timeout_seconds)
        self.session = session or requests.Session()

    def create_job(
        self,
        *,
        prompt: str,
        model: str,
        image_url: Optional[str] = None,
        webhook_url: Optional[str] = None,
        user_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "model": model,
        }
        if image_url:
            payload["image_url"] = image_url
        if webhook_url:
            payload["webhook_url"] = webhook_url
        if user_id:
            payload["user_id"] = user_id
        if extra:
            payload.update(extra)

        resp = self.session.post(
            self.generate_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json()

    def get_job(self, job_id: str) -> Dict[str, Any]:
        url = f"{self.jobs_base_url}{job_id}"
        resp = self.session.get(
            url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=max(self.timeout_seconds, 60),
        )
        resp.raise_for_status()
        return resp.json()

    def wait_for_job(
        self,
        job_id: str,
        *,
        timeout_seconds: int = 180,
        poll_interval_seconds: int = 5,
    ) -> ImageJobResult:
        deadline = time.time() + int(timeout_seconds)
        last: Optional[Dict[str, Any]] = None

        while time.time() < deadline:
            last = self.get_job(job_id)
            status = str(last.get("status", "")).lower().strip()

            if status == "completed":
                return ImageJobResult(
                    job_id=job_id,
                    status=status,
                    result_url=last.get("result_url") or last.get("url"),
                    raw=last,
                )

            if status in {"failed", "error", "canceled", "cancelled"}:
                raise RuntimeError(f"Image job {job_id} failed: {last}")

            time.sleep(int(poll_interval_seconds))

        raise TimeoutError(f"Image job {job_id} did not complete within {timeout_seconds}s: {last}")

    def generate_image(
        self,
        *,
        prompt: str,
        model: str,
        image_url: Optional[str] = None,
        webhook_url: Optional[str] = None,
        user_id: Optional[str] = None,
        timeout_seconds: int = 180,
        poll_interval_seconds: int = 5,
    ) -> str:
        created = self.create_job(
            prompt=prompt,
            model=model,
            image_url=image_url,
            webhook_url=webhook_url,
            user_id=user_id,
        )

        job_id = created.get("job_id") or created.get("id")
        if not job_id:
            raise RuntimeError(f"create_job did not return job_id: {created}")

        result = self.wait_for_job(
            str(job_id),
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

        if not result.result_url:
            raise RuntimeError(f"Image job completed but no result_url: {result.raw}")

        return str(result.result_url)
