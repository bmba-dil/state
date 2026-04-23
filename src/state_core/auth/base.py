"""AuthMethod protocol + Credential container."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict


class Credential(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = ""
    access: str = ""
    expires: float = 0.0


class AuthMethod(Protocol):
    async def login(self) -> Credential: ...
    async def refresh(self, cred: Credential) -> Credential: ...
    def is_expired(self, cred: Credential, now: float) -> bool: ...
