from pydantic import BaseModel
from typing import Optional

class UpdatePostDto(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None