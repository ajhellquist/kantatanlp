# Tool definition for logging time entry using names
schema = {
    "type": "function",
    "function": {
        "name": "log_time_entry_by_name",
        "description": (
            "Create a Kantata time entry using names instead of IDs. "
            "This is easier to use as you don't need to know the specific IDs. "
            "The system will automatically look up the correct IDs for you. "
            "IMPORTANT: When the user mentions 'yesterday', 'today', 'tomorrow', "
            "or similar date terms, extract and use those exact terms as the date parameter."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_name": {"type": "string", "description": "The user's name (e.g., 'John Smith', 'john', 'smith')"},
                "project_name": {"type": "string", "description": "The project name (e.g., 'Big Bend Medical', 'Big Bend')"},
                "task_name": {"type": "string", "description": "The task name (optional, e.g., 'Design Review', 'Bug Fix')"},
                "hours": {"type": "number", "description": "Number of hours worked"},
                "billable": {"type": "boolean", "description": "Whether the time is billable"},
                "date": {"type": "string", "description": "Date for the time entry. Use 'yesterday', 'today', 'tomorrow', or specific date in YYYY-MM-DD format. IMPORTANT: If user says 'yesterday', use 'yesterday' as the date parameter."},
                "notes": {"type": "string", "description": "Notes for the time entry"}
            },
            "required": ["user_name", "project_name", "hours", "billable", "date", "notes"]
        }
    }
}
