from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from datetime import datetime, date, timedelta
import httpx

from ..config import TOKEN, HEADERS, BASE_URL
from ..kantata import lookup_user, lookup_workspace, lookup_story

router = APIRouter()

class TimeEntryByNamePayload(BaseModel):
    user_name: str
    project_name: str
    task_name: str | None = None
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

@router.post("/time_entry_by_name")
async def create_time_entry_by_name(payload: TimeEntryByNamePayload):
    if not TOKEN:
        raise HTTPException(500, "KANTATA_API_TOKEN not set")

    user = await lookup_user(payload.user_name)
    workspace = await lookup_workspace(payload.project_name)
    story_id = None
    if payload.task_name:
        story = await lookup_story(workspace["workspace_id"], payload.task_name)
        story_id = story["story_id"]

    time_entry_data = {
        "time_entry": {
            "user_id": user["user_id"],
            "workspace_id": workspace["workspace_id"],
            "story_id": story_id,
            "date_performed": payload.date,
            "time_in_minutes": int(payload.hours * 60),
            "billable": payload.billable,
            "notes": payload.notes,
        }
    }

    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        r = await client.post("/time_entries.json", json=time_entry_data)
        if r.status_code not in (200, 201):
            raise HTTPException(r.status_code, r.text)

    data = r.json()
    entry_id = data.get("results", ["?"])[0]
    return {
        "status": "success",
        "entry_id": entry_id,
        "minutes": int(payload.hours * 60),
        "date": payload.date,
        "user_id": user["user_id"],
        "user_name": user["name"],
        "project_name": workspace["name"],
        "task_name": payload.task_name,
    }
