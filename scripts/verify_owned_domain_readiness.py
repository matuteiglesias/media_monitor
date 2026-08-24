#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def fetch_json(url: str, timeout: float = 20.0) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "media-monitor-domain-readiness/1"})
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{url}: expected JSON object")
    return payload


def verify(owned_url: str, provider_url: str) -> dict:
    owned = owned_url.rstrip("/")
    provider = provider_url.rstrip("/")
    owned_host = urlparse(owned).hostname
    if not owned_host:
        raise ValueError("owned URL has no hostname")

    addresses = sorted({item[4][0] for item in socket.getaddrinfo(owned_host, 443, type=socket.SOCK_STREAM)})
    if not addresses:
        raise ValueError("owned hostname does not resolve")

    owned_health = fetch_json(f"{owned}/api/health")
    provider_health = fetch_json(f"{provider}/api/health")
    for label, health in (("owned", owned_health), ("provider", provider_health)):
        if health.get("status") != "ok":
            raise ValueError(f"{label} health is not ok")
        if health.get("site_id") != "argentina-general":
            raise ValueError(f"{label} health points to unexpected site")
    if owned_health.get("snapshot_id") != provider_health.get("snapshot_id"):
        raise ValueError("owned and provider hosts do not serve the same snapshot")

    return {
        "schema_name": "owned_domain_readiness.v1",
        "status": "ready",
        "owned_url": owned,
        "provider_url": provider,
        "resolved_addresses": addresses,
        "snapshot_id": owned_health.get("snapshot_id"),
        "current_canonical_url": owned_health.get("canonical_url"),
        "next_action": "Set GitHub Actions variable CANONICAL_OWNED_DOMAIN_ACTIVE=1 and let the next production roll rebuild the canonical surface.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owned-url", required=True)
    parser.add_argument("--provider-url", required=True)
    args = parser.parse_args()
    try:
        report = verify(args.owned_url, args.provider_url)
    except Exception as exc:
        print(json.dumps({"schema_name": "owned_domain_readiness.v1", "status": "not_ready", "error": str(exc)}))
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
