from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SWOT(BaseModel):
    strengths: List[str]
    weaknesses: List[str]
    opportunities: List[str]
    threats: List[str]


class PESTEL(BaseModel):
    political: List[str]
    economic: List[str]
    social: List[str]
    technological: List[str]
    environmental: List[str]
    legal: List[str]


class Competitor(BaseModel):
    name: str
    summary: Optional[str] = None
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    product: str
    market_summary: str
    swot: SWOT
    pestel: PESTEL
    competitors: List[Competitor]
    raw_sources: Dict[str, int]  # e.g. counts per platform
