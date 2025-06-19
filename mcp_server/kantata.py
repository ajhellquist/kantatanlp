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
