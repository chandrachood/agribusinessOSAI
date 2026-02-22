from datetime import date
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from ..models.product import Product
from ..pipelines.banking_pipeline import run_banking_pipeline
from ..services.time_window import resolve_time_window
from ..utils.ids import new_id

router = APIRouter(prefix="/analyze", tags=["analyze"])


class AnalyzeRequest(BaseModel):
    product_name: str
    product_url: Optional[HttpUrl] = None
    region: str = "UK"
    segment: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@router.post("")
async def analyze(req: AnalyzeRequest):
    start_date, end_date = resolve_time_window(req.start_date, req.end_date)
    product = Product(
        id=new_id(),
        name=req.product_name,
        url=req.product_url,
        country=req.region,
        segment=req.segment,
    )
    try:
        report = run_banking_pipeline(product, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return report
