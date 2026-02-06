"""
SociClaw CLI helpers.

This is NOT the final OpenClaw command-dispatch integration, but it provides a
reproducible way to exercise the local stack:
- Provision an image account/API key for a provider user id
- Generate an image using the provisioned API key

Examples (PowerShell):
  $env:OPENCLAW_PROVISION_SECRET="..."
  python -m sociclaw.scripts.cli provision-image --provider telegram --provider-user-id 123


  python -m sociclaw.scripts.cli whoami --provider telegram --provider-user-id 123

  python -m sociclaw.scripts.cli generate-image --provider telegram --provider-user-id 123 --prompt "a blue bird logo"
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional

from .provisioning_client import ProvisioningClient
from .provisioning_gateway import SociClawProvisioningGatewayClient
from .image_generator import ImageGenerator
from .state_store import StateStore


def _redact_secret(secret: Optional[str]) -> Optional[str]:
    if not secret:
        return secret
    s = str(secret)
    if len(s) <= 8:
        return "***"
    return f"{s[:4]}...{s[-4:]}"


def cmd_provision_image(args: argparse.Namespace) -> int:
    openclaw_secret = args.openclaw_secret or os.getenv("OPENCLAW_PROVISION_SECRET")
    if not openclaw_secret:
        raise SystemExit("Missing OPENCLAW_PROVISION_SECRET (env) or --openclaw-secret")
    if not args.url:
        raise SystemExit("Missing provisioning --url or env SOCICLAW_PROVISION_UPSTREAM_URL")

    client = ProvisioningClient(openclaw_secret=openclaw_secret, url=args.url)
    res = client.provision(
        provider=args.provider,
        provider_user_id=str(args.provider_user_id),
        create_api_key=True,
    )

    store = StateStore(Path(args.state_path) if args.state_path else None)
    store.upsert_user(
        provider=res.provider,
        provider_user_id=res.provider_user_id,
        image_api_key=res.api_key,
        wallet_address=res.wallet_address,
    )

    print(
        json.dumps(
            {
                "provider": res.provider,
                "provider_user_id": res.provider_user_id,
                "api_key": _redact_secret(res.api_key),
                "wallet_address": res.wallet_address,
                "state_path": str(store.path),
            },
            indent=2,
        )
    )
    return 0


def cmd_whoami(args: argparse.Namespace) -> int:
    store = StateStore(Path(args.state_path) if args.state_path else None)
    u = store.get_user(provider=args.provider, provider_user_id=str(args.provider_user_id))
    if not u:
        print(json.dumps({"found": False, "state_path": str(store.path)}, indent=2))
        return 1

    print(
        json.dumps(
            {
                "found": True,
                "provider": u.provider,
                "provider_user_id": u.provider_user_id,
                "image_api_key": _redact_secret(u.image_api_key),
                "wallet_address": u.wallet_address,
                "created_at": u.created_at,
                "updated_at": u.updated_at,
                "state_path": str(store.path),
            },
            indent=2,
        )
    )
    return 0


def cmd_generate_image(args: argparse.Namespace) -> int:
    store = StateStore(Path(args.state_path) if args.state_path else None)
    u = store.get_user(provider=args.provider, provider_user_id=str(args.provider_user_id))
    if not u or not u.image_api_key:
        raise SystemExit(
            "Missing provisioned user API key. Run: provision-image "
            f"--provider {args.provider} --provider-user-id {args.provider_user_id}"
        )

    out_dir = Path(args.output_dir) if args.output_dir else None
    gen = ImageGenerator(
        api_key=u.image_api_key,
        model=args.model,
        output_dir=out_dir,
        # Provider manages billing/credits on its side; we do not enforce PaymentHandler here.
        payment_handler=None,
    )

    # user_address is just an identifier for the upstream image API ("user_id" field)
    r = gen.generate_image(args.prompt, user_address=f"{u.provider}:{u.provider_user_id}")
    print(json.dumps({"url": r.url, "local_path": str(r.local_path) if r.local_path else None}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sociclaw", description="SociClaw CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_prov = sub.add_parser("provision-image", help="Provision image account/API key for a provider user id")
    p_prov.add_argument("--provider", required=True, help="e.g. telegram")
    p_prov.add_argument("--provider-user-id", required=True, help="e.g. Telegram user id")
    p_prov.add_argument(
        "--openclaw-secret",
        default=None,
        help="Optional. If omitted, uses env OPENCLAW_PROVISION_SECRET.",
    )
    p_prov.add_argument(
        "--url",
        default=os.getenv("SOCICLAW_PROVISION_UPSTREAM_URL"),
        help="Provisioning URL",
    )
    p_prov.add_argument("--state-path", default=None, help="Override state path (defaults to .tmp/sociclaw_state.json)")
    p_prov.set_defaults(func=cmd_provision_image)

    p_prox = sub.add_parser(
        "provision-image-gateway",
        help="Provision via your backend gateway (recommended; keeps OPENCLAW_PROVISION_SECRET server-side)",
    )
    p_prox.add_argument("--provider", required=True, help="e.g. telegram")
    p_prox.add_argument("--provider-user-id", required=True, help="e.g. Telegram user id")
    p_prox.add_argument(
        "--url",
        default=os.getenv("SOCICLAW_PROVISION_URL"),
        help="Gateway URL (e.g. https://api.sociclaw.com/api/sociclaw/provision)",
    )
    p_prox.add_argument(
        "--internal-token",
        default=os.getenv("SOCICLAW_INTERNAL_TOKEN"),
        help="Optional. Use only if your gateway requires server-side auth.",
    )
    p_prox.add_argument("--state-path", default=None, help="Override state path (defaults to .tmp/sociclaw_state.json)")

    def cmd_gateway(args: argparse.Namespace) -> int:
        if not args.url:
            raise SystemExit("Missing gateway --url or env SOCICLAW_PROVISION_URL")

        client = SociClawProvisioningGatewayClient(
            url=args.url,
            internal_token=args.internal_token or None,
        )
        res = client.provision(
            provider=args.provider,
            provider_user_id=str(args.provider_user_id),
            create_api_key=True,
        )

        store = StateStore(Path(args.state_path) if args.state_path else None)
        store.upsert_user(
            provider=res.provider,
            provider_user_id=res.provider_user_id,
            image_api_key=res.api_key,
            wallet_address=res.wallet_address,
        )

        print(
            json.dumps(
                {
                    "provider": res.provider,
                    "provider_user_id": res.provider_user_id,
                    "api_key": _redact_secret(res.api_key),
                    "wallet_address": res.wallet_address,
                    "state_path": str(store.path),
                },
                indent=2,
            )
        )
        return 0

    p_prox.set_defaults(func=cmd_gateway)

    p_who = sub.add_parser("whoami", help="Show locally stored provisioned info for a provider user id")
    p_who.add_argument("--provider", required=True)
    p_who.add_argument("--provider-user-id", required=True)
    p_who.add_argument("--state-path", default=None)
    p_who.set_defaults(func=cmd_whoami)

    p_img = sub.add_parser("generate-image", help="Generate an image using the provisioned API key")
    p_img.add_argument("--provider", required=True)
    p_img.add_argument("--provider-user-id", required=True)
    p_img.add_argument("--prompt", required=True)
    p_img.add_argument(
        "--model",
        default=(
            os.getenv("SOCICLAW_IMAGE_MODEL")
            or "nano-banana"
        ),
    )
    p_img.add_argument("--output-dir", default=None)
    p_img.add_argument("--state-path", default=None)
    p_img.set_defaults(func=cmd_generate_image)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
