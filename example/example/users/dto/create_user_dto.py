from pydantic import BaseModel, field_validator
from typing import List

class CreateUserDto(BaseModel):
    name: str
    email: str
    password: str
    roles: List[str] = ["user"]

    @field_validator("password")
    @classmethod
    def min_length(cls, v):
        if len(v) < 6: raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("roles")
    @classmethod
    def valid_roles(cls, v):
        allowed = {"admin", "user", "moderator"}
        for r in v:
            if r not in allowed: raise ValueError(f"Invalid role '{r}'")
        return v