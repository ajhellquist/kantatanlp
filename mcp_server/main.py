from fastapi import FastAPI, HTTPException
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

from .config import TOKEN
from .kantata import search_workspaces, search_stories, search_users
from .handlers import routers

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Kantata MCP POC")

for r in routers:
    app.include_router(r)

# --- Helper functions for Kantata API lookups ---

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
