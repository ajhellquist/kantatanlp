from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, date, timedelta
import httpx, os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Kantata MCP POC")

BASE_URL = "https://api.mavenlink.com/api/v1"
TOKEN    = os.getenv("KANTATA_API_TOKEN")
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}

# --- Helper functions for Kantata API lookups ---
async def search_workspaces(name: str) -> list:
    """Search for workspaces (projects) by name"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        r = await client.get("/workspaces.json", params={"search": name})
        if r.status_code == 200:
            data = r.json()
            return data.get("workspaces", {})
        return {}

async def search_stories(workspace_id: int, name: str = None) -> list:
    """Search for stories (tasks) by name within a workspace"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        params = {"workspace_id": workspace_id}
        if name:
            params["search"] = name
        r = await client.get("/stories.json", params=params)
        if r.status_code == 200:
            data = r.json()
            return data.get("stories", {})
        return {}

async def search_users(name: str) -> list:
    """Search for users by name"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        r = await client.get("/users.json", params={"search": name})
        if r.status_code == 200:
            data = r.json()
            return data.get("users", {})
        return {}

# --- Lookup endpoints ---
@app.get("/lookup/workspace/{name}")
async def lookup_workspace(name: str):
    """Look up workspace ID by name"""
    if not TOKEN:
        raise HTTPException(500, "KANTATA_API_TOKEN not set")
    
    workspaces = await search_workspaces(name)
    if workspaces:
        # Return the first match
        workspace_id = list(workspaces.keys())[0]
        workspace_data = workspaces[workspace_id]
        return {
            "workspace_id": int(workspace_id),
            "name": workspace_data.get("title", name),
            "description": workspace_data.get("description", "")
        }
    else:
        raise HTTPException(404, f"No workspace found with name containing '{name}'")

@app.get("/lookup/story/{workspace_id}/{name}")
async def lookup_story(workspace_id: int, name: str):
    """Look up story ID by name within a workspace"""
    if not TOKEN:
        raise HTTPException(500, "KANTATA_API_TOKEN not set")
    
    stories = await search_stories(workspace_id, name)
    if stories:
        # Return the first match
        story_id = list(stories.keys())[0]
        story_data = stories[story_id]
        return {
            "story_id": int(story_id),
            "name": story_data.get("title", name),
            "workspace_id": workspace_id
        }
    else:
        raise HTTPException(404, f"No story found with name containing '{name}' in workspace {workspace_id}")

@app.get("/lookup/user/{name}")
async def lookup_user(name: str):
    """Look up user ID by name"""
    if not TOKEN:
        raise HTTPException(500, "KANTATA_API_TOKEN not set")
    
    users = await search_users(name)
    if users:
        # Return the first match
        user_id = list(users.keys())[0]
        user_data = users[user_id]
        print(f"DEBUG: Raw user data from Kantata API: {user_data}")
        
        # Try different possible field names for the name
        user_name = ""
        if user_data.get('first_name') and user_data.get('last_name'):
            user_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
        elif user_data.get('name'):
            user_name = user_data.get('name')
        elif user_data.get('full_name'):
            user_name = user_data.get('full_name')
        elif user_data.get('display_name'):
            user_name = user_data.get('display_name')
        else:
            # Fallback to the search term if no name found
            user_name = name
            
        print(f"DEBUG: Constructed user name: '{user_name}'")
        
        return {
            "user_id": int(user_id),
            "name": user_name,
            "email": user_data.get("email", "")
        }
    else:
        raise HTTPException(404, f"No user found with name containing '{name}'")

@app.post("/resolve_date")
async def resolve_date(date_request: dict):
    """Resolve a date string to an actual date"""
    from dateutil import parser
    from datetime import date
    
    date_str = date_request.get("date", "today")
    print(f"DEBUG: Resolving date string: '{date_str}'")
    
    # Handle common natural language dates
    date_lower = date_str.lower().strip()
    if date_lower in ["today", "now"]:
        result = date.today().isoformat()
        print(f"DEBUG: Resolved '{date_str}' as today: {result}")
        return {"resolved_date": result}
    elif date_lower == "yesterday":
        result = (date.today() - timedelta(days=1)).isoformat()
        print(f"DEBUG: Resolved '{date_str}' as yesterday: {result}")
        return {"resolved_date": result}
    elif date_lower == "tomorrow":
        result = (date.today() + timedelta(days=1)).isoformat()
        print(f"DEBUG: Resolved '{date_str}' as tomorrow: {result}")
        return {"resolved_date": result}
    
    try:
        # Try ISO format first
        dt = datetime.fromisoformat(date_str)
        result = dt.date().isoformat()
        print(f"DEBUG: Resolved '{date_str}' as ISO format: {result}")
        return {"resolved_date": result}
    except ValueError:
        try:
            # Try natural language parsing
            dt = parser.parse(date_str, fuzzy=True)
            result = dt.date().isoformat()
            print(f"DEBUG: Resolved '{date_str}' with dateutil: {result}")
            return {"resolved_date": result}
        except Exception as e:
            # If all parsing fails, default to today
            result = date.today().isoformat()
            print(f"Warning: Could not parse date '{date_str}': {e}. Using today's date: {result}")
            return {"resolved_date": result}

# --- Enhanced time entry with name lookups ---
class TimeEntryByNamePayload(BaseModel):
    user_name:    str
    project_name: str
    task_name:    str | None = None
    hours:        float
    billable:     bool
    date:         str
    notes:        str

    # --- validators ---------------------------------------------------------
    @field_validator("date")
    @classmethod
    def iso_date(cls, v):
        from dateutil import parser
        from datetime import date
        
        print(f"DEBUG: Received date string: '{v}'")
        
        # Handle common natural language dates
        v_lower = v.lower().strip()
        if v_lower in ["today", "now"]:
            result = date.today().isoformat()
            print(f"DEBUG: Parsed '{v}' as today: {result}")
            return result
        elif v_lower == "yesterday":
            result = (date.today() - timedelta(days=1)).isoformat()
            print(f"DEBUG: Parsed '{v}' as yesterday: {result}")
            return result
        elif v_lower == "tomorrow":
            result = (date.today() + timedelta(days=1)).isoformat()
            print(f"DEBUG: Parsed '{v}' as tomorrow: {result}")
            return result
        
        try:
            # Try ISO format first
            dt = datetime.fromisoformat(v)
            result = dt.date().isoformat()
            print(f"DEBUG: Parsed '{v}' as ISO format: {result}")
            return result
        except ValueError:
            try:
                # Try natural language parsing
                dt = parser.parse(v, fuzzy=True)
                result = dt.date().isoformat()
                print(f"DEBUG: Parsed '{v}' with dateutil: {result}")
                return result
            except Exception as e:
                # If all parsing fails, default to today
                result = date.today().isoformat()
                print(f"Warning: Could not parse date '{v}': {e}. Using today's date: {result}")
                return result

@app.post("/time_entry_by_name")
async def create_time_entry_by_name(payload: TimeEntryByNamePayload):
    """Create time entry using names instead of IDs"""
    if not TOKEN:
        raise HTTPException(500, "KANTATA_API_TOKEN not set")

    # Look up user ID
    user_response = await lookup_user(payload.user_name)
    user_id = user_response["user_id"]
    
    # Look up workspace ID
    workspace_response = await lookup_workspace(payload.project_name)
    workspace_id = workspace_response["workspace_id"]
    
    # Look up story ID if task name provided
    story_id = None
    if payload.task_name:
        story_response = await lookup_story(workspace_id, payload.task_name)
        story_id = story_response["story_id"]
    
    # Create the time entry
    time_entry_data = {
        "time_entry": {
            "user_id":          user_id,
            "workspace_id":     workspace_id,
            "story_id":         story_id,
            "date_performed":   payload.date,
            "time_in_minutes":  int(payload.hours * 60),
            "billable":         payload.billable,
            "notes":            payload.notes,
        }
    }
    
    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        r = await client.post("/time_entries.json", json=time_entry_data)
        if r.status_code not in (200, 201):
            raise HTTPException(r.status_code, r.text)

    data = r.json()
    entry_id = data.get("results", ["?"])[0]
    return {
        "status":  "success",
        "entry_id": entry_id,
        "minutes": int(payload.hours * 60),
        "date":    payload.date,
        "user_id": user_id,
        "user_name": user_response["name"],
        "project_name": workspace_response["name"],
        "task_name": story_response["name"] if payload.task_name else None
    }

# --- Original time entry endpoint (for backward compatibility) ---
class TimeEntryPayload(BaseModel):
    user_id:      int
    workspace_id: int = Field(..., alias="project_id")
    story_id:     int | None = Field(None, alias="task_id")
    hours:        float
    billable:     bool
    date:         str
    notes:        str

    # --- validators ---------------------------------------------------------
    @field_validator("date")
    @classmethod
    def iso_date(cls, v):
        from dateutil import parser
        from datetime import date
        
        print(f"DEBUG: Received date string: '{v}'")
        
        # Handle common natural language dates
        v_lower = v.lower().strip()
        if v_lower in ["today", "now"]:
            result = date.today().isoformat()
            print(f"DEBUG: Parsed '{v}' as today: {result}")
            return result
        elif v_lower == "yesterday":
            result = (date.today() - timedelta(days=1)).isoformat()
            print(f"DEBUG: Parsed '{v}' as yesterday: {result}")
            return result
        elif v_lower == "tomorrow":
            result = (date.today() + timedelta(days=1)).isoformat()
            print(f"DEBUG: Parsed '{v}' as tomorrow: {result}")
            return result
        
        try:
            # Try ISO format first
            dt = datetime.fromisoformat(v)
            result = dt.date().isoformat()
            print(f"DEBUG: Parsed '{v}' as ISO format: {result}")
            return result
        except ValueError:
            try:
                # Try natural language parsing
                dt = parser.parse(v, fuzzy=True)
                result = dt.date().isoformat()
                print(f"DEBUG: Parsed '{v}' with dateutil: {result}")
                return result
            except Exception as e:
                # If all parsing fails, default to today
                result = date.today().isoformat()
                print(f"Warning: Could not parse date '{v}': {e}. Using today's date: {result}")
                return result

    # --- Kantata request body ----------------------------------------------
    def kantata_body(self) -> dict:
        return {
            "time_entry": {
                "user_id":          self.user_id,
                "workspace_id":     self.workspace_id,
                "story_id":         self.story_id,
                "date_performed":   self.date,
                "time_in_minutes":  int(self.hours * 60),
                "billable":         self.billable,
                "notes":            self.notes,
            }
        }

@app.post("/time_entry")
async def create_time_entry(payload: TimeEntryPayload):
    """Create time entry using IDs (original endpoint)"""
    if not TOKEN:
        raise HTTPException(500, "KANTATA_API_TOKEN not set")

    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        r = await client.post("/time_entries.json", json=payload.kantata_body())
        if r.status_code not in (200, 201):
            raise HTTPException(r.status_code, r.text)

    data = r.json()
    entry_id = data.get("results", ["?"])[0]
    return {
        "status":  "success",
        "entry_id": entry_id,
        "minutes": int(payload.hours * 60),
        "date":    payload.date,
        "user_id": payload.user_id
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
