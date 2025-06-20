from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, date, timedelta
from typing import Optional
import asyncio

from ..config import TOKEN
from ..kantata import (
    fetch_time_entries, get_user_name, get_workspace_name, get_story_name,
    lookup_user, lookup_workspace, lookup_story
)

router = APIRouter()

class TimeEntryQuery(BaseModel):
    time_period: str
    user_name: Optional[str] = None
    project_name: Optional[str] = None
    task_name: Optional[str] = None

def parse_time_period(time_period: str) -> tuple[str, str]:
    """Parse natural language time period into start and end dates."""
    period_lower = time_period.lower().strip()
    today = date.today()
    
    # Month name mapping
    month_names = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }
    
    if period_lower == "today":
        return today.isoformat(), today.isoformat()
    elif period_lower == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday.isoformat(), yesterday.isoformat()
    elif period_lower == "this week":
        # Monday to Sunday
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)
        return monday.isoformat(), sunday.isoformat()
    elif period_lower == "last week":
        # Previous Monday to Sunday
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)
        return last_monday.isoformat(), last_sunday.isoformat()
    elif period_lower == "this month":
        # First day to last day of current month
        first_day = today.replace(day=1)
        if today.month == 12:
            last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        return first_day.isoformat(), last_day.isoformat()
    elif period_lower == "last month":
        # First day to last day of previous month
        if today.month == 1:
            first_day = today.replace(year=today.year - 1, month=12, day=1)
        else:
            first_day = today.replace(month=today.month - 1, day=1)
        last_day = today.replace(day=1) - timedelta(days=1)
        return first_day.isoformat(), last_day.isoformat()
    elif period_lower == "this year":
        # January 1 to December 31 of current year
        first_day = today.replace(month=1, day=1)
        last_day = today.replace(month=12, day=31)
        return first_day.isoformat(), last_day.isoformat()
    elif " to " in period_lower:
        # Custom date range
        try:
            start_str, end_str = period_lower.split(" to ")
            start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d").date()
            return start_date.isoformat(), end_date.isoformat()
        except ValueError:
            raise HTTPException(400, f"Invalid date range format: {time_period}. Use YYYY-MM-DD to YYYY-MM-DD")
    
    # Handle month names like "june 2025", "january 2024", etc.
    words = period_lower.split()
    if len(words) == 2:
        month_word, year_word = words
        if month_word in month_names and year_word.isdigit():
            month_num = month_names[month_word]
            year_num = int(year_word)
            if 1900 <= year_num <= 2100:  # Reasonable year range
                first_day = date(year_num, month_num, 1)
                if month_num == 12:
                    last_day = date(year_num + 1, 1, 1) - timedelta(days=1)
                else:
                    last_day = date(year_num, month_num + 1, 1) - timedelta(days=1)
                return first_day.isoformat(), last_day.isoformat()
    
    # Try to parse as a single date
    try:
        parsed_date = datetime.strptime(period_lower, "%Y-%m-%d").date()
        return parsed_date.isoformat(), parsed_date.isoformat()
    except ValueError:
        raise HTTPException(400, f"Unrecognized time period: {time_period}. Supported formats: 'today', 'this week', 'this month', 'june 2025', '2025-06-01 to 2025-06-30', etc.")

def format_time_entries_table(entries: list, start_date: str, end_date: str) -> str:
    """Format time entries into a beautiful table grouped by week."""
    if not entries:
        return f"No time entries found for {start_date} to {end_date}"
    
    # Group entries by week
    weeks = {}
    for entry_id, entry_data in entries.items():
        entry_date = entry_data.get("date_performed", "")
        if entry_date:
            try:
                date_obj = datetime.strptime(entry_date, "%Y-%m-%d").date()
                # Get the Monday of the week
                days_since_monday = date_obj.weekday()
                monday = date_obj - timedelta(days=days_since_monday)
                week_key = monday.isoformat()
                
                if week_key not in weeks:
                    weeks[week_key] = []
                weeks[week_key].append((entry_id, entry_data))
            except ValueError:
                continue
    
    # Sort weeks
    sorted_weeks = sorted(weeks.keys())
    
    output = []
    total_entries = 0
    total_hours = 0
    total_billable_hours = 0
    
    for week_start in sorted_weeks:
        week_entries = weeks[week_start]
        week_entries.sort(key=lambda x: x[1].get("date_performed", ""))
        
        # Format week header
        monday_date = datetime.strptime(week_start, "%Y-%m-%d").date()
        sunday_date = monday_date + timedelta(days=6)
        week_header = f"=== Week of {monday_date.strftime('%B %d, %Y')} ==="
        output.append(week_header)
        
        # Create table header
        table_header = "┌─────────────┬────────────┬─────────────────┬─────────────────┬───────┬──────────┬─────────────────────┐"
        header_row = "│ User        │ Date       │ Project         │ Task            │ Hours │ Billable │ Notes               │"
        separator = "├─────────────┼────────────┼─────────────────┼─────────────────┼───────┼──────────┼─────────────────────┤"
        table_footer = "└─────────────┴────────────┴─────────────────┴─────────────────┴───────┴──────────┴─────────────────────┘"
        
        output.append(table_header)
        output.append(header_row)
        output.append(separator)
        
        # Add entries for this week
        for entry_id, entry_data in week_entries:
            user_name = entry_data.get("user_name", "Unknown")
            date_performed = entry_data.get("date_performed", "")
            project_name = entry_data.get("project_name", "Unknown")
            task_name = entry_data.get("task_name", "")
            hours = entry_data.get("hours", 0)
            billable = "Yes" if entry_data.get("billable", False) else "No"
            notes = entry_data.get("notes", "") or ""  # Handle None values
            notes = notes[:18]  # Truncate long notes
            
            # Truncate long names
            user_name = user_name[:11] if len(user_name) > 11 else user_name.ljust(11)
            project_name = project_name[:15] if len(project_name) > 15 else project_name.ljust(15)
            task_name = task_name[:15] if len(task_name) > 15 else task_name.ljust(15)
            notes = notes[:18] if len(notes) > 18 else notes.ljust(18)
            
            row = f"│ {user_name} │ {date_performed} │ {project_name} │ {task_name} │ {hours:5.1f} │ {billable:8} │ {notes} │"
            output.append(row)
            
            total_entries += 1
            total_hours += hours
            if entry_data.get("billable", False):
                total_billable_hours += hours
        
        output.append(table_footer)
        output.append("")  # Empty line between weeks
    
    # Add summary
    output.append("📊 SUMMARY")
    output.append(f"Total Entries: {total_entries}")
    output.append(f"Total Hours: {total_hours:.1f}")
    output.append(f"Billable Hours: {total_billable_hours:.1f}")
    
    return "\n".join(output)

@router.post("/query_time_entries")
async def query_time_entries(payload: TimeEntryQuery):
    """Query time entries with natural language processing and beautiful formatting."""
    if not TOKEN:
        raise HTTPException(500, "KANTATA_API_TOKEN not set")
    
    try:
        print(f"DEBUG: Starting query for {payload.time_period}")
        
        # Parse time period
        start_date, end_date = parse_time_period(payload.time_period)
        print(f"DEBUG: Date range: {start_date} to {end_date}")
        
        # Resolve user name to ID if provided (but don't use as API filter)
        user_id = None
        if payload.user_name:
            try:
                print(f"DEBUG: Looking up user: {payload.user_name}")
                user_info = await lookup_user(payload.user_name)
                user_id = user_info["user_id"]
                print(f"DEBUG: Found user ID: {user_id}")
            except HTTPException as e:
                print(f"DEBUG: User lookup failed: {e}")
                # If user lookup fails, continue without user filter
                pass
        
        # Resolve project name to ID if provided
        workspace_id = None
        if payload.project_name:
            try:
                print(f"DEBUG: Looking up workspace: {payload.project_name}")
                workspace_info = await lookup_workspace(payload.project_name)
                workspace_id = workspace_info["workspace_id"]
                print(f"DEBUG: Found workspace ID: {workspace_id}")
            except HTTPException as e:
                print(f"DEBUG: Workspace lookup failed: {e}")
                # If workspace lookup fails, continue without workspace filter
                pass
        
        # Resolve task name to ID if provided
        story_id = None
        if payload.task_name and workspace_id:
            try:
                print(f"DEBUG: Looking up story: {payload.task_name}")
                story_info = await lookup_story(workspace_id, payload.task_name)
                story_id = story_info["story_id"]
                print(f"DEBUG: Found story ID: {story_id}")
            except HTTPException as e:
                print(f"DEBUG: Story lookup failed: {e}")
                # If story lookup fails, continue without story filter
                pass
        
        # Fetch time entries using API filters to minimise result size
        print(f"DEBUG: Fetching time entries...")
        entries = await fetch_time_entries(start_date, end_date, user_id, workspace_id, story_id)
        print(f"DEBUG: Found {len(entries)} entries")
        
        if not entries:
            return {
                "status": "success",
                "time_period": payload.time_period,
                "start_date": start_date,
                "end_date": end_date,
                "formatted_output": f"No time entries found for {start_date} to {end_date}",
                "total_entries": 0
            }
        
        # Debug: Show structure of first entry
        if entries:
            first_entry_id = list(entries.keys())[0]
            first_entry = entries[first_entry_id]
            print(f"DEBUG: Sample entry structure: {first_entry}")
        
        # Filter by date_performed and user if specified
        filtered_entries = {}
        for entry_id, entry_data in entries.items():
            entry_user_id = entry_data.get("user_id")
            entry_date_performed = entry_data.get("date_performed")
            print(f"DEBUG: Entry {entry_id} has user_id: {entry_user_id}, date_performed: {entry_date_performed}")
            
            # Check if entry is within the requested date range
            if entry_date_performed and start_date <= entry_date_performed <= end_date:
                # If user filter is specified, only include entries for that user
                if user_id is not None:
                    # Convert both to strings for comparison (API returns string, lookup returns int)
                    if str(entry_user_id) == str(user_id):
                        filtered_entries[entry_id] = entry_data
                else:
                    # No user filter, include all entries
                    filtered_entries[entry_id] = entry_data
        
        print(f"DEBUG: After date and user filtering: {len(filtered_entries)} entries")
        
        # For now, let's create a simplified response without resolving all IDs
        # This will help us identify if the issue is with the API calls or the formatting
        resolved_entries = {}
        for entry_id, entry_data in filtered_entries.items():
            try:
                print(f"DEBUG: Processing entry {entry_id}")
                
                # Convert minutes to hours
                minutes = entry_data.get("time_in_minutes", 0)
                hours = minutes / 60.0
                
                # Get actual names instead of IDs
                user_id_for_lookup = entry_data.get("user_id", 0)
                workspace_id_for_lookup = entry_data.get("workspace_id", 0)
                story_id_for_lookup = entry_data.get("story_id")
                
                print(f"DEBUG: Looking up user name for ID: {user_id_for_lookup}")
                user_name = await get_user_name(user_id_for_lookup)
                print(f"DEBUG: Got user name: {user_name}")
                
                print(f"DEBUG: Looking up workspace name for ID: {workspace_id_for_lookup}")
                workspace_name = await get_workspace_name(workspace_id_for_lookup)
                print(f"DEBUG: Got workspace name: {workspace_name}")
                
                # Get story name if present
                task_name = ""
                if story_id_for_lookup:
                    print(f"DEBUG: Looking up story name for ID: {story_id_for_lookup}")
                    task_name = await get_story_name(story_id_for_lookup)
                    print(f"DEBUG: Got story name: {task_name}")
                
                # Create resolved entry with actual names
                resolved_entries[entry_id] = {
                    "user_name": user_name,
                    "date_performed": entry_data.get("date_performed", ""),
                    "project_name": workspace_name,
                    "task_name": task_name,
                    "hours": hours,
                    "billable": entry_data.get("billable", False),
                    "notes": entry_data.get("notes", "") or ""
                }
                print(f"DEBUG: Created resolved entry: {resolved_entries[entry_id]}")
            except Exception as e:
                print(f"Warning: Failed to process entry {entry_id}: {e}")
                continue
        
        print(f"DEBUG: Processed {len(resolved_entries)} entries")
        
        # Format the results
        formatted_output = format_time_entries_table(resolved_entries, start_date, end_date)
        
        return {
            "status": "success",
            "time_period": payload.time_period,
            "start_date": start_date,
            "end_date": end_date,
            "formatted_output": formatted_output,
            "total_entries": len(resolved_entries)
        }
        
    except Exception as e:
        print(f"Error in query_time_entries: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}") 