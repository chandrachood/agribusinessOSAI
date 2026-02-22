from typing import Optional
from pydantic import BaseModel, HttpUrl


class Product(BaseModel):
    id: str
    name: str
    country: str = "UK"
    url: Optional[HttpUrl] = None
    segment: Optional[str] = None  # e.g. retail, SME, etc.
    notes: Optional[str] = None
