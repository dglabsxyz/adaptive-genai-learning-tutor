"""State integrity protection using HMAC signatures.

AGT-022, WEB-030: Protects persisted state files (learner data, checkpoints,
exercise stores) from tampering by adding HMAC signatures that are verified on load.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("backend.state_integrity")

# Default key for local development - production should use TUTOR_STATE_HMAC_KEY env var
_DEFAULT_KEY = "tutor-state-integrity-dev-key-change-in-production"


def _get_hmac_key() -> bytes:
    """Get the HMAC key from environment or use default for local development."""
    key = os.getenv("TUTOR_STATE_HMAC_KEY", _DEFAULT_KEY)
    if key == _DEFAULT_KEY and os.getenv("TUTOR_ENV", "local").lower() in {"prod", "production"}:
        logger.warning(
            "Using default HMAC key in production! Set TUTOR_STATE_HMAC_KEY environment variable. (AGT-022)"
        )
    return key.encode("utf-8")


def compute_signature(data: bytes) -> str:
    """Compute HMAC-SHA256 signature for data."""
    return hmac.new(_get_hmac_key(), data, hashlib.sha256).hexdigest()


def verify_signature(data: bytes, signature: str) -> bool:
    """Verify HMAC-SHA256 signature for data."""
    expected = compute_signature(data)
    return hmac.compare_digest(expected, signature)


def sign_json(data: dict[str, Any]) -> dict[str, Any]:
    """Add HMAC signature to JSON data.

    Returns a new dict with __signature__ field added.
    """
    # Remove any existing signature before computing
    data_copy = {k: v for k, v in data.items() if k != "__signature__"}
    # Canonical JSON encoding (sorted keys, no extra whitespace)
    canonical = json.dumps(data_copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = compute_signature(canonical)
    return {**data_copy, "__signature__": signature}


def verify_json(data: dict[str, Any], *, strict: bool = False) -> tuple[bool, dict[str, Any]]:
    """Verify HMAC signature on JSON data.

    Returns (valid, data_without_signature). If no signature present and strict=False,
    returns (True, data) to allow migration from unsigned data.
    """
    signature = data.get("__signature__")
    data_copy = {k: v for k, v in data.items() if k != "__signature__"}

    if signature is None:
        if strict:
            logger.warning("State file missing integrity signature (AGT-022)")
            return False, data_copy
        # Allow unsigned data for backwards compatibility (migration period)
        return True, data_copy

    canonical = json.dumps(data_copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    valid = verify_signature(canonical, signature)
    if not valid:
        logger.error("State file integrity check FAILED - possible tampering detected (AGT-022)")
    return valid, data_copy


def sign_file(path: Path) -> None:
    """Add HMAC signature to an existing JSON file."""
    if not path.exists():
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Cannot sign file %s: %s", path, exc)
        return

    if not isinstance(data, dict):
        logger.warning("Cannot sign non-dict JSON file: %s", path)
        return

    signed = sign_json(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(signed, f, indent=2)


def verify_file(path: Path, *, strict: bool = False) -> tuple[bool, dict[str, Any] | None]:
    """Verify HMAC signature on a JSON file.

    Returns (valid, data) or (False, None) if file cannot be read.
    """
    if not path.exists():
        return True, None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Cannot read file %s for verification: %s", path, exc)
        return False, None

    if not isinstance(data, dict):
        return True, data  # Non-dict files don't have signatures

    valid, clean_data = verify_json(data, strict=strict)
    return valid, clean_data


class IntegrityProtectedStore:
    """Wrapper for JSON file stores with HMAC integrity protection."""

    def __init__(self, path: Path, *, strict: bool = False):
        self.path = path
        self.strict = strict

    def load(self) -> dict[str, Any]:
        """Load and verify the JSON file."""
        if not self.path.exists():
            return {}

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load %s: %s", self.path, exc)
            return {}

        if not isinstance(data, dict):
            return data

        valid, clean_data = verify_json(data, strict=self.strict)
        if not valid and self.strict:
            raise ValueError(f"Integrity verification failed for {self.path}")

        return clean_data

    def save(self, data: dict[str, Any]) -> None:
        """Sign and save the JSON file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        signed = sign_json(data)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(signed, f, indent=2)
