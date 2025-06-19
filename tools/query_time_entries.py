# Tool definition for querying time entries
schema = {
    "type": "function",
    "function": {
        "name": "query_time_entries",
        "description": (
            "Query time entries from Kantata for a given time period. Accepts natural language "
            "time periods like 'this week', 'this month', 'last week', 'yesterday', etc. "
            "Can filter by user name, project name, and task name. Returns formatted results "
            "grouped by week with user names, project names, and task names (not IDs)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "time_period": {
                    "type": "string", 
                    "description": "Time period to query. Examples: 'this week', 'this month', 'last week', 'yesterday', 'last month', 'this year', or specific date range like '2024-01-01 to 2024-01-31'"
                },
                "user_name": {
                    "type": "string", 
                    "description": "Optional: Filter by user name (e.g., 'John Doe', 'Sarah Smith')"
                },
                "project_name": {
                    "type": "string", 
                    "description": "Optional: Filter by project/workspace name"
                },
                "task_name": {
                    "type": "string", 
                    "description": "Optional: Filter by task/story name"
                }
            },
            "required": ["time_period"]
        }
    }
} 