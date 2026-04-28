from pydantic import BaseModel, field_validator

class RegisterDto(BaseModel):
    name: str
    email: str
    password: str

    @field_validator("password")
    @classmethod
    def min_length(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v