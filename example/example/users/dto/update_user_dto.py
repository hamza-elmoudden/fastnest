from pydantic import BaseModel, field_validator
from typing import Optional, List

class UpdateUserDto(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[List[str]] = None

    @field_validator("roles")
    @classmethod
    def valid_roles(cls, v):
        if v is None: return v
        allowed = {"admin", "user", "moderator"}
        for r in v:
            if r not in allowed: raise ValueError(f"Invalid role '{r}'")
        return v