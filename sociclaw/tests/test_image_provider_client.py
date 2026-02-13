import requests
import pytest

from sociclaw.scripts.image_provider_client import ImageProviderClient


def _response(status: int, payload: dict, *, headers: dict | None = None) -> requests.Response:
    resp = requests.Response()
    resp.status_code = status
    resp._content = __import__("json").dumps(payload).encode("utf-8")
    resp.headers.update(headers or {"Content-Type": "application/json"})
    resp.url = "https://image.example.com/api/v1?path=generate"
    return resp


def test_create_job_retries_with_image_data_url_payload(monkeypatch):
    post_payloads: list[dict] = []

    def fake_request_with_retry(**kwargs):
        if kwargs["method"] == "POST":
            post_payloads.append(kwargs["json"])
            if len(post_payloads) == 1:
                return _response(422, {"error": "Nano Banana model requires an image input (image_data_url or image_url)"})
            return _response(200, {"job_id": "job_123"})
        raise AssertionError("unexpected method")

    monkeypatch.setattr("sociclaw.scripts.image_provider_client.request_with_retry", fake_request_with_retry)
    monkeypatch.setattr(
        "sociclaw.scripts.image_provider_client.ImageProviderClient._resolve_image_data_url",
        lambda self, image_url: "data:image/png;base64,AAAA",
    )

    client = ImageProviderClient(
        api_key="sk_test",
        generate_url="https://image.example.com/api/v1?path=generate",
        jobs_base_url="https://image.example.com/api/v1/jobs/",
    )

    created = client.create_job(prompt="test", model="nano-banana", image_url="https://cdn.example.com/logo.png")
    assert created["job_id"] == "job_123"
    assert len(post_payloads) == 2
    assert post_payloads[0]["image_url"] == "https://cdn.example.com/logo.png"
    assert post_payloads[1]["image_data_url"].startswith("data:image/png;base64,")


def test_create_job_does_not_retry_on_auth_error(monkeypatch):
    post_calls = {"count": 0}

    def fake_request_with_retry(**kwargs):
        post_calls["count"] += 1
        return _response(401, {"error": "Unauthorized"})

    monkeypatch.setattr("sociclaw.scripts.image_provider_client.request_with_retry", fake_request_with_retry)
    monkeypatch.setattr(
        "sociclaw.scripts.image_provider_client.ImageProviderClient._resolve_image_data_url",
        lambda self, image_url: "data:image/png;base64,AAAA",
    )

    client = ImageProviderClient(
        api_key="sk_test",
        generate_url="https://image.example.com/api/v1?path=generate",
        jobs_base_url="https://image.example.com/api/v1/jobs/",
    )

    with pytest.raises(requests.HTTPError):
        client.create_job(prompt="test", model="nano-banana", image_url="https://cdn.example.com/logo.png")

    assert post_calls["count"] == 1


def test_resolve_image_data_url_keeps_data_url():
    client = ImageProviderClient(
        api_key="sk_test",
        generate_url="https://image.example.com/api/v1?path=generate",
        jobs_base_url="https://image.example.com/api/v1/jobs/",
    )

    value = "data:image/png;base64,AAAA"
    assert client._resolve_image_data_url(value) == value


def test_resolve_image_data_url_from_local_path(monkeypatch, tmp_path):
    monkeypatch.setenv("SOCICLAW_ALLOW_ABSOLUTE_IMAGE_INPUT_DIRS", "true")
    monkeypatch.setenv("SOCICLAW_ALLOWED_IMAGE_INPUT_DIRS", str(tmp_path))
    client = ImageProviderClient(
        api_key="sk_test",
        generate_url="https://image.example.com/api/v1?path=generate",
        jobs_base_url="https://image.example.com/api/v1/jobs/",
    )
    image_path = tmp_path / "logo.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")

    resolved = client._resolve_image_data_url(str(image_path))
    assert isinstance(resolved, str)
    assert resolved.startswith("data:image/png;base64,")


def test_resolve_image_data_url_blocks_disallowed_local_path(tmp_path):
    client = ImageProviderClient(
        api_key="sk_test",
        generate_url="https://image.example.com/api/v1?path=generate",
        jobs_base_url="https://image.example.com/api/v1/jobs/",
    )
    assert client._resolve_image_data_url(str(tmp_path / "secret.txt")) is None


def test_allowed_image_input_dirs_ignores_absolute_paths_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("SOCICLAW_ALLOW_ABSOLUTE_IMAGE_INPUT_DIRS", raising=False)
    monkeypatch.setenv("SOCICLAW_ALLOWED_IMAGE_INPUT_DIRS", str(tmp_path))
    client = ImageProviderClient(
        api_key="sk_test",
        generate_url="https://image.example.com/api/v1?path=generate",
        jobs_base_url="https://image.example.com/api/v1/jobs/",
    )
    assert all(str(p) != str(tmp_path) for p in client.allowed_input_roots)


def test_resolve_image_data_url_blocks_remote_when_disabled(monkeypatch):
    monkeypatch.setenv("SOCICLAW_ALLOW_IMAGE_URL_INPUT", "false")
    client = ImageProviderClient(
        api_key="sk_test",
        generate_url="https://image.example.com/api/v1?path=generate",
        jobs_base_url="https://image.example.com/api/v1/jobs/",
    )
    assert client._resolve_image_data_url("https://example.com/logo.png") is None


def test_resolve_image_data_url_blocks_remote_without_allowlist(monkeypatch):
    monkeypatch.setenv("SOCICLAW_ALLOW_IMAGE_URL_INPUT", "true")
    monkeypatch.delenv("SOCICLAW_ALLOWED_IMAGE_URL_HOSTS", raising=False)

    calls = {"n": 0}

    def fake_fetch(self, url: str):
        calls["n"] += 1
        return b"\x89PNG\r\n\x1a\nfake", "image/png", url

    monkeypatch.setattr(ImageProviderClient, "_fetch_remote_image_bytes", fake_fetch)

    client = ImageProviderClient(
        api_key="sk_test",
        generate_url="https://image.example.com/api/v1?path=generate",
        jobs_base_url="https://image.example.com/api/v1/jobs/",
    )
    assert client._resolve_image_data_url("https://example.com/logo.png") is None
    assert calls["n"] == 0


def test_resolve_image_data_url_allows_remote_with_allowlist(monkeypatch):
    monkeypatch.setenv("SOCICLAW_ALLOW_IMAGE_URL_INPUT", "true")
    monkeypatch.setenv("SOCICLAW_ALLOWED_IMAGE_URL_HOSTS", "example.com")

    def fake_fetch(self, url: str):
        return b"\x89PNG\r\n\x1a\nfake", "image/png", url

    monkeypatch.setattr(ImageProviderClient, "_fetch_remote_image_bytes", fake_fetch)

    client = ImageProviderClient(
        api_key="sk_test",
        generate_url="https://image.example.com/api/v1?path=generate",
        jobs_base_url="https://image.example.com/api/v1/jobs/",
    )
    resolved = client._resolve_image_data_url("https://example.com/logo.png")
    assert isinstance(resolved, str)
    assert resolved.startswith("data:image/png;base64,")


def test_resolve_image_data_url_blocks_remote_not_in_allowlist(monkeypatch):
    monkeypatch.setenv("SOCICLAW_ALLOW_IMAGE_URL_INPUT", "true")
    monkeypatch.setenv("SOCICLAW_ALLOWED_IMAGE_URL_HOSTS", "example.com")

    calls = {"n": 0}

    def fake_fetch(self, url: str):
        calls["n"] += 1
        return b"\x89PNG\r\n\x1a\nfake", "image/png", url

    monkeypatch.setattr(ImageProviderClient, "_fetch_remote_image_bytes", fake_fetch)

    client = ImageProviderClient(
        api_key="sk_test",
        generate_url="https://image.example.com/api/v1?path=generate",
        jobs_base_url="https://image.example.com/api/v1/jobs/",
    )
    assert client._resolve_image_data_url("https://evil.com/logo.png") is None
    assert calls["n"] == 0
