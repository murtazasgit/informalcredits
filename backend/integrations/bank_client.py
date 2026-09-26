"""
HTTP client for the separate Bank Partner API (bank-partner-api/).
Base URL and API key come from the environment so no secret is hard-coded in the app:
  BANK_API_URL (default http://localhost:8100)   BANK_API_KEY (default dev-bank-key, MVP mock)
"""
import os

import httpx


class BankApiError(Exception):
    """Bank service unreachable, rejected our key, or returned an unexpected response."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _client() -> httpx.Client:
    """Factory kept separate so tests can swap in an in-process client."""
    return httpx.Client(
        base_url=os.environ.get("BANK_API_URL", "http://localhost:8100"),
        headers={"X-API-Key": os.environ.get("BANK_API_KEY", "dev-bank-key")},
        timeout=5.0,
    )


def _call(method: str, path: str, **kwargs) -> dict:
    try:
        with _client() as client:
            response = client.request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        raise BankApiError(f"Bank partner API unreachable: {exc}") from exc
    if response.status_code == 404:
        raise BankApiError("Application not found at bank partner", 404)
    if response.status_code in (401, 403):
        raise BankApiError("Bank partner rejected our API key")
    if response.status_code >= 400:
        raise BankApiError(f"Bank partner error {response.status_code}: {response.text[:200]}")
    return response.json()


def preapprove(payload: dict) -> dict:
    return _call("POST", "/preapprove", json=payload)


def offer_status(application_id: str) -> dict:
    return _call("GET", f"/offer-status/{application_id}")
