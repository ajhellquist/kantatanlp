from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, date, timedelta

from ..config import TOKEN, HEADERS, BASE_URL
import httpx

router = APIRouter()

class TimeEntryPayload(BaseModel):
    user_id: int
    workspace_id: int = Field(..., alias="project_id")
    story_id: int | None = Field(None, alias="task_id")
    hours: float
    billable: bool
    date: str
    notes: str

    @field_validator("date")
    @classmethod
    def iso_date(cls, v):
        from dateutil import parser
        v_lower = v.lower().strip()
        if v_lower in ["today", "now"]:
            return date.today().isoformat()
        if v_lower == "yesterday":
            return (date.today() - timedelta(days=1)).isoformat()
        if v_lower == "tomorrow":
            return (date.today() + timedelta(days=1)).isoformat()
        try:
            dt = datetime.fromisoformat(v)
            return dt.date().isoformat()
        except ValueError:
            try:
                dt = parser.parse(v, fuzzy=True)
                return dt.date().isoformat()
            except Exception:
                return date.today().isoformat()

    def kantata_body(self) -> dict:
        return {
            "time_entry": {
                "user_id": self.user_id,
                "workspace_id": self.workspace_id,
                "story_id": self.story_id,
                "date_performed": self.date,
                "time_in_minutes": int(self.hours * 60),
                "billable": self.billable,
                "notes": self.notes,
            }
        }

@router.post("/time_entry")
async def create_time_entry(payload: TimeEntryPayload):
    if not TOKEN:
        raise HTTPException(500, "KANTATA_API_TOKEN not set")
    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        r = await client.post("/time_entries.json", json=payload.kantata_body())
        if r.status_code not in (200, 201):
            raise HTTPException(r.status_code, r.text)
    data = r.json()
    entry_id = data.get("results", ["?"])[0]
    return {
        "status": "success",
        "entry_id": entry_id,
        "minutes": int(payload.hours * 60),
        "date": payload.date,
        "user_id": payload.user_id,
    }
