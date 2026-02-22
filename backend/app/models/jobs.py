from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel
from .report import AnalysisReport

JobStatus = Literal["queued", "running", "completed", "failed"]


class Job(BaseModel):
    id: str
    status: JobStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    report: Optional[AnalysisReport] = None
    error: Optional[str] = None
