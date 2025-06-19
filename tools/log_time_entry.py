# Tool definition for logging time entry by IDs
schema = {
    "type": "function",
    "function": {
        "name": "log_time_entry",
        "description": (
            "Create a Kantata time entry via MCP. When the user mentions 'today', "
            "'today's date', or similar, use 'today' as the date parameter. When "
            "no specific date is mentioned, default to 'today'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "The user ID for the time entry"},
                "project_id": {"type": "integer", "description": "The project/workspace ID"},
                "task_id": {"type": "integer", "description": "The task/story ID (optional)"},
                "hours": {"type": "number", "description": "Number of hours worked"},
                "billable": {"type": "boolean", "description": "Whether the time is billable"},
                "date": {"type": "string", "description": "Date for the time entry. Use 'today' for current date, or specific date in YYYY-MM-DD format"},
                "notes": {"type": "string", "description": "Notes for the time entry"}
            },
            "required": ["user_id", "project_id", "hours", "billable", "date", "notes"]
        }
    }
}
