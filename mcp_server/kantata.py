"""Utility functions for interacting with the Kantata API."""
import httpx
from fastapi import HTTPException
from .config import BASE_URL, HEADERS, TOKEN

async def search_workspaces(name: str) -> list:
    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        r = await client.get("/workspaces.json", params={"search": name})
        if r.status_code == 200:
            return r.json().get("workspaces", {})
        return {}

async def search_stories(workspace_id: int, name: str | None = None) -> list:
    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        params = {"workspace_id": workspace_id}
        if name:
            params["search"] = name
        r = await client.get("/stories.json", params=params)
        if r.status_code == 200:
            return r.json().get("stories", {})
        return {}

async def search_users(name: str) -> list:
    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        r = await client.get("/users.json", params={"search": name})
        if r.status_code == 200:
            return r.json().get("users", {})
        return {}

async def fetch_time_entries(
    start_date: str,
    end_date: str,
    user_id: int | None = None,
    workspace_id: int | None = None,
    story_id: int | None = None,
) -> tuple[dict, dict]:
    """Fetch all time entries from Kantata API handling pagination with included related data."""
    if not TOKEN:
        raise HTTPException(500, "KANTATA_API_TOKEN not set")

    entries: dict = {}
    included_data: dict = {"users": {}, "workspaces": {}, "stories": {}}
    page = 1
    per_page = 200  # Increased from 100 to reduce number of pages

    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=60) as client:  # Increased timeout to 60s
        while True:
            params = {
                "date_performed_between": f"{start_date}:{end_date}",
                "per_page": per_page,
                "page": page,
                "include": "user,workspace,story",  # Include related data to avoid extra API calls
            }

            if user_id:
                params["with_user_ids"] = user_id
            if workspace_id:
                params["workspace_id"] = workspace_id
            if story_id:
                params["story_id"] = story_id

            r = await client.get("/time_entries.json", params=params)
            if r.status_code != 200:
                break

            data = r.json()
            page_entries = data.get("time_entries", {})
            entries.update(page_entries)
            
            # Collect included data from each page
            if "users" in data:
                included_data["users"].update(data["users"])
            if "workspaces" in data:
                included_data["workspaces"].update(data["workspaces"])
            if "stories" in data:
                included_data["stories"].update(data["stories"])

            # Determine if there is another page.  The Kantata API includes a
            # "next" link in the response headers when more results are
            # available.  If the header is missing or the returned page has
            # fewer results than requested, stop fetching.
            link_header = r.headers.get("Link", "")
            has_next = "rel=\"next\"" in link_header or data.get("next_page")

            if not has_next or len(page_entries) < per_page:
                break

            page += 1

    return entries, included_data

async def get_user_name(user_id: int) -> str:
    """Get user name by ID."""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=30) as client:
            r = await client.get(f"/users/{user_id}.json")
            print(f"DEBUG: get_user_name({user_id}) status={r.status_code}")
            print(f"DEBUG: get_user_name({user_id}) raw response: {r.text}")
            if r.status_code == 200:
                response_data = r.json()
                # The API returns data under 'users' key, then under the user ID
                users_data = response_data.get("users", {})
                user_data = users_data.get(str(user_id), {})
                print(f"DEBUG: get_user_name({user_id}) user_data={user_data}")
                if not user_data:
                    print(f"WARNING: get_user_name({user_id}) user_data is empty!")
                if user_data.get("first_name") and user_data.get("last_name"):
                    return f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
                elif user_data.get("name"):
                    return user_data["name"]
                elif user_data.get("full_name"):
                    return user_data["full_name"]
                elif user_data.get("display_name"):
                    return user_data["display_name"]
            else:
                print(f"DEBUG: get_user_name({user_id}) failed, response={r.text}")
    except Exception as e:
        print(f"ERROR: get_user_name({user_id}) exception: {e}")
    return f"User {user_id}"

async def get_workspace_name(workspace_id: int) -> str:
    """Get workspace name by ID."""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=30) as client:
            r = await client.get(f"/workspaces/{workspace_id}.json")
            print(f"DEBUG: get_workspace_name({workspace_id}) status={r.status_code}")
            print(f"DEBUG: get_workspace_name({workspace_id}) raw response: {r.text}")
            if r.status_code == 200:
                response_data = r.json()
                # The API returns data under 'workspaces' key, then under the workspace ID
                workspaces_data = response_data.get("workspaces", {})
                workspace_data = workspaces_data.get(str(workspace_id), {})
                print(f"DEBUG: get_workspace_name({workspace_id}) workspace_data={workspace_data}")
                if not workspace_data:
                    print(f"WARNING: get_workspace_name({workspace_id}) workspace_data is empty!")
                return workspace_data.get("title", f"Workspace {workspace_id}")
            else:
                print(f"DEBUG: get_workspace_name({workspace_id}) failed, response={r.text}")
    except Exception as e:
        print(f"ERROR: get_workspace_name({workspace_id}) exception: {e}")
    return f"Workspace {workspace_id}"

async def get_story_name(story_id: int) -> str:
    """Get story name by ID."""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=30) as client:
            r = await client.get(f"/stories/{story_id}.json")
            print(f"DEBUG: get_story_name({story_id}) status={r.status_code}")
            print(f"DEBUG: get_story_name({story_id}) raw response: {r.text}")
            if r.status_code == 200:
                response_data = r.json()
                # The API returns data under 'stories' key, then under the story ID
                stories_data = response_data.get("stories", {})
                story_data = stories_data.get(str(story_id), {})
                print(f"DEBUG: get_story_name({story_id}) story_data={story_data}")
                if not story_data:
                    print(f"WARNING: get_story_name({story_id}) story_data is empty!")
                return story_data.get("title", f"Story {story_id}")
            else:
                print(f"DEBUG: get_story_name({story_id}) failed, response={r.text}")
    except Exception as e:
        print(f"ERROR: get_story_name({story_id}) exception: {e}")
    return f"Story {story_id}"

async def lookup_workspace(name: str) -> dict:
    if not TOKEN:
        raise HTTPException(500, "KANTATA_API_TOKEN not set")
    workspaces = await search_workspaces(name)
    if workspaces:
        workspace_id = list(workspaces.keys())[0]
        workspace_data = workspaces[workspace_id]
        return {
            "workspace_id": int(workspace_id),
            "name": workspace_data.get("title", name),
            "description": workspace_data.get("description", ""),
        }
    raise HTTPException(404, f"No workspace found with name containing '{name}'")

async def lookup_story(workspace_id: int, name: str) -> dict:
    if not TOKEN:
        raise HTTPException(500, "KANTATA_API_TOKEN not set")
    stories = await search_stories(workspace_id, name)
    if stories:
        story_id = list(stories.keys())[0]
        story_data = stories[story_id]
        return {
            "story_id": int(story_id),
            "name": story_data.get("title", name),
            "workspace_id": workspace_id,
        }
    raise HTTPException(404, f"No story found with name containing '{name}' in workspace {workspace_id}")

async def lookup_user(name: str) -> dict:
    if not TOKEN:
        raise HTTPException(500, "KANTATA_API_TOKEN not set")
    users = await search_users(name)
    if users:
        user_id = list(users.keys())[0]
        user_data = users[user_id]
        user_name = ""
        if user_data.get("first_name") and user_data.get("last_name"):
            user_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
        elif user_data.get("name"):
            user_name = user_data["name"]
        elif user_data.get("full_name"):
            user_name = user_data["full_name"]
        elif user_data.get("display_name"):
            user_name = user_data["display_name"]
        else:
            user_name = name
        return {
            "user_id": int(user_id),
            "name": user_name,
            "email": user_data.get("email", ""),
        }
    raise HTTPException(404, f"No user found with name containing '{name}'")
