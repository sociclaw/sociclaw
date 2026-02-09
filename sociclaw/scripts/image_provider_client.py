"""
Image Provider API client (Internal).

This client handles image generation API calls.
The underlying provider details are abstracted away from user-facing code.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

import requests

from .http_retry import request_with_retry

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
        self.max_retries = int(os.getenv("SOCICLAW_HTTP_MAX_RETRIES", "3"))
        self.backoff_base_seconds = float(os.getenv("SOCICLAW_HTTP_BACKOFF_SECONDS", "0.5"))
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
        base_payload: Dict[str, Any] = {
            "prompt": prompt,
            "model": model,
        }
        if image_url:
            base_payload["image_url"] = image_url
        if webhook_url:
            base_payload["webhook_url"] = webhook_url
        if user_id:
            base_payload["user_id"] = user_id
        if extra:
            base_payload.update(extra)

        payload_candidates = [base_payload]
        if image_url:
            image_data_url = self._resolve_image_data_url(image_url)
            if image_data_url:
                payload_with_data_url = dict(base_payload)
                payload_with_data_url["image_data_url"] = image_data_url
                payload_candidates.append(payload_with_data_url)

                payload_data_only = dict(base_payload)
                payload_data_only.pop("image_url", None)
                payload_data_only["image_data_url"] = image_data_url
                payload_candidates.append(payload_data_only)

        last_response: Optional[requests.Response] = None
        for idx, payload in enumerate(payload_candidates):
            resp = request_with_retry(
                session=self.session,
                method="POST",
                url=self.generate_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self.timeout_seconds,
                max_retries=self.max_retries,
                backoff_base_seconds=self.backoff_base_seconds,
            )
            if resp.ok:
                return resp.json()

            last_response = resp
            has_fallback = idx < (len(payload_candidates) - 1)
            if has_fallback and self._should_retry_with_alternate_payload(resp):
                logger.warning(
                    "Generate request failed (%s). Retrying with alternate image payload format.",
                    resp.status_code,
                )
                continue

            resp.raise_for_status()

        if last_response is not None:
            last_response.raise_for_status()
        raise RuntimeError("Image API create_job failed without response")

    def _should_retry_with_alternate_payload(self, response: requests.Response) -> bool:
        if response.status_code not in {400, 422}:
            return False
        body = (response.text or "").lower()
        return any(
            token in body
            for token in (
                "image input",
                "image_url",
                "image_data_url",
                "missing image",
                "requires an image",
            )
        )

    def _resolve_image_data_url(self, image_url: str) -> Optional[str]:
        clean = str(image_url or "").strip()
        if not clean:
            return None
        if clean.startswith("data:image/"):
            return clean

        local_path = self._resolve_local_path(clean)
        if local_path and local_path.is_file():
            try:
                data = local_path.read_bytes()
            except OSError:
                return None
            return self._build_image_data_url(data, source_hint=str(local_path), content_type_hint=None)

        disable = (os.getenv("SOCICLAW_DISABLE_IMAGE_DATA_URL_FALLBACK") or "").strip().lower()
        if disable in {"1", "true", "yes", "on"}:
            return None

        try:
            resp = request_with_retry(
                session=self.session,
                method="GET",
                url=clean,
                timeout=self.timeout_seconds,
                max_retries=1,
                backoff_base_seconds=self.backoff_base_seconds,
            )
            if not resp.ok or not resp.content:
                return None
        except requests.RequestException:
            return None

        content_type = (resp.headers.get("Content-Type", "") or "").split(";")[0].strip().lower()
        return self._build_image_data_url(resp.content, source_hint=clean, content_type_hint=content_type)

    def _resolve_local_path(self, image_input: str) -> Optional[Path]:
        value = str(image_input or "").strip()
        if not value:
            return None

        if value.lower().startswith("file://"):
            parsed = urlparse(value)
            if parsed.scheme != "file":
                return None
            file_path = unquote(parsed.path or "")
            if os.name == "nt" and file_path.startswith("/"):
                file_path = file_path[1:]
            return Path(file_path)

        try:
            candidate = Path(value)
        except (TypeError, ValueError):
            return None
        return candidate

    def _build_image_data_url(
        self,
        data: bytes,
        *,
        source_hint: str,
        content_type_hint: Optional[str],
    ) -> Optional[str]:
        if not data:
            return None
        if len(data) > 10 * 1024 * 1024:
            logger.warning("Input image too large for data URL fallback (%s bytes)", len(data))
            return None

        content_type = (content_type_hint or "").split(";")[0].strip().lower()
        if not content_type.startswith("image/"):
            guessed, _ = mimetypes.guess_type(source_hint)
            if guessed and guessed.startswith("image/"):
                content_type = guessed
            else:
                content_type = "image/png"

        encoded = base64.b64encode(data).decode("ascii")
        return f"data:{content_type};base64,{encoded}"

    def get_job(self, job_id: str) -> Dict[str, Any]:
        url = f"{self.jobs_base_url}{job_id}"
        resp = request_with_retry(
            session=self.session,
            method="GET",
            url=url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=max(self.timeout_seconds, 60),
            max_retries=self.max_retries,
            backoff_base_seconds=self.backoff_base_seconds,
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
