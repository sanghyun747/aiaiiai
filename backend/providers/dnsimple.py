"""DNSimple adapter. No token is available on this machine.

Without DNSIMPLE_API_TOKEN this returns an explicit provider_not_configured
error. It NEVER reports sandbox_record_created without a real API response,
and never overwrites or deletes an existing record.
"""
from __future__ import annotations

import os

import httpx

from .errors import ProviderError

DEFAULT_BASE = "https://api.sandbox.dnsimple.com/v2"


def is_configured() -> bool:
    return bool(os.environ.get("DNSIMPLE_API_TOKEN") and os.environ.get("DNSIMPLE_ACCOUNT_ID"))


def _headers():
    return {
        "Authorization": f"Bearer {os.environ['DNSIMPLE_API_TOKEN']}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def create_cname(name: str, target_hostname: str, client: httpx.Client = None) -> dict:
    """Create one CNAME in the sandbox zone and read it back.

    target_hostname must be a hostname, never a URL path.
    Raises ProviderError if unconfigured or if a conflicting record exists.
    """
    if not is_configured():
        raise ProviderError(
            "DNS_NOT_CONFIGURED",
            "DNSimple is not configured on this machine (no DNSIMPLE_API_TOKEN/ACCOUNT_ID). "
            "No DNS record was created.",
            False,
        )
    if "/" in target_hostname or ":" in target_hostname:
        raise ProviderError("EVIDENCE_INVALID", "A CNAME target must be a hostname, not a URL.", False)
    base = os.environ.get("DNSIMPLE_BASE_URL", DEFAULT_BASE)
    account = os.environ["DNSIMPLE_ACCOUNT_ID"]
    zone = os.environ.get("DNSIMPLE_ZONE", "")
    owns_client = client is None
    client = client or httpx.Client(timeout=30.0)
    try:
        existing = client.get(
            f"{base}/{account}/zones/{zone}/records",
            headers=_headers(), params={"name": name, "type": "CNAME"},
        )
        if existing.status_code >= 400:
            raise ProviderError("PROVIDER_UNAVAILABLE", f"DNSimple read failed: HTTP {existing.status_code}", True)
        rows = existing.json().get("data") or []
        for row in rows:
            if row.get("content", "").rstrip(".") != target_hostname.rstrip("."):
                raise ProviderError(
                    "EVIDENCE_INVALID",
                    "An existing record conflicts with the expected target; review required. "
                    "Nothing was overwritten or deleted.",
                    False,
                )
            return {"record_id": str(row.get("id")), "readback": row, "created": False}
        created = client.post(
            f"{base}/{account}/zones/{zone}/records",
            headers=_headers(),
            json={"name": name, "type": "CNAME", "content": target_hostname, "ttl": 3600},
        )
        if created.status_code >= 400:
            raise ProviderError("PROVIDER_UNAVAILABLE", f"DNSimple create failed: HTTP {created.status_code}", True)
        record = created.json()["data"]
        readback = client.get(
            f"{base}/{account}/zones/{zone}/records/{record['id']}", headers=_headers()
        )
        if readback.status_code >= 400:
            raise ProviderError("PROVIDER_UNAVAILABLE", "DNSimple readback failed; creation unverified.", True)
        return {"record_id": str(record["id"]), "readback": readback.json().get("data"), "created": True}
    finally:
        if owns_client:
            client.close()
