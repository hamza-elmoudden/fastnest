from pydantic import BaseModel

class LoginDto(BaseModel):
    email: str
    password: str