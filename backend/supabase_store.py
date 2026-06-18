"""Optional Supabase adapter placeholder.

The MVP uses local JSON files. This module documents the production switch
point without adding a hard runtime dependency or requiring secrets.
"""

from __future__ import annotations

from dataclasses import dataclass

from .settings import get_settings


@dataclass
class SupabaseSettings:
    url: str
    service_role_key: str


def get_supabase_settings() -> SupabaseSettings | None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    return SupabaseSettings(url=settings.supabase_url, service_role_key=settings.supabase_service_role_key)


def supabase_enabled() -> bool:
    return get_supabase_settings() is not None
