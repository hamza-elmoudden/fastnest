from pydantic import BaseModel, field_validator

class CreatePostDto(BaseModel):
    title: str
    content: str

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v):
        if not v.strip(): raise ValueError("Title cannot be empty")
        return v.strip()