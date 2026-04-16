from pydantic import BaseModel
from typing import Optional
from datetime import date
import uuid


class Activity(BaseModel):
    id: Optional[uuid.UUID] = None
    date: date
    source: str = "manual"
    description: str
    contact_id: Optional[uuid.UUID] = None
    strategic_score: int = 0
    strategic_flags: list[str] = []
    created_by: str


class Contact(BaseModel):
    id: Optional[uuid.UUID] = None
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    tier: Optional[str] = None
    role_stage: int = 1
    last_touched: Optional[date] = None
    days_stalled: int = 0
    status: str = "active"
    pipeline_track: str = "global_south"


class Commitment(BaseModel):
    id: Optional[uuid.UUID] = None
    contact_id: Optional[uuid.UUID] = None
    description: str
    due_date: Optional[date] = None
    promised_by: str
    status: str = "open"


class LogActivityInput(BaseModel):
    text: str
    created_by: str
    source: str = "manual"


class AddCommitmentInput(BaseModel):
    description: str
    due_date: Optional[date] = None
    promised_by: str
    contact_name: Optional[str] = None


class CorrectEntryInput(BaseModel):
    entry_type: str  # activity, commitment, contact, artifact
    entry_id: str
    field: str
    new_value: str


class ScoreActivityInput(BaseModel):
    description: str
