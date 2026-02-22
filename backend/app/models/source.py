from typing import Literal
from pydantic import BaseModel, HttpUrl

SourceType = Literal["trustpilot", "app_store", "play_store", "reddit", "mse"]


class Source(BaseModel):
    id: str
    name: str
    type: SourceType
    base_url: HttpUrl
    weight: float  # ranking priority
