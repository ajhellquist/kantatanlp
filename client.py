import os, json, sys, requests, openai, readline
from dotenv import load_dotenv
from tools import schemas as functions

# Load environment variables from .env file
load_dotenv()

MCP_URL        = "http://localhost:8000/time_entry"

# Check for OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    print("❌ OpenAI API key not found!")
    print("Please set your OpenAI API key in your .env file:")
    print("OPENAI_API_KEY=your-api-key-here")
    sys.exit(1)

# ---------------- OpenAI function schema -----------------

messages=[{"role":"system",
           "content":"You are an assistant that logs time to Kantata OX. When users mention 'today', 'today's date', or similar phrases, always use 'today' as the date parameter. When no specific date is mentioned, default to 'today'. Always extract the date parameter from the user's request and include it in the function call."}]

# Initialize OpenAI client
client = openai.OpenAI()

def chat(user_input:str):
    messages.append({"role":"user","content":user_input})
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=functions,
        tool_choice="auto"
    )
    msg = resp.choices[0].message
    
    # Add the assistant's message to the conversation history
    messages.append(msg)
    
    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        print(f"↳ OpenAI called {tool_call.function.name} with {args}")
        
        # Handle different tool types
        if tool_call.function.name == "query_time_entries":
            # Handle time entry queries - no confirmation needed
            try:
                r = requests.post("http://localhost:8000/query_time_entries", json=args, timeout=60)
                if r.ok:
                    res = r.json()
                    print("\n" + "="*80)
                    print("📊 TIME ENTRIES QUERY RESULTS")
                    print("="*80)
                    print(res['formatted_output'])
                    print("="*80)
                    messages.append({"role":"tool",
                                     "tool_call_id": tool_call.id,
                                     "name": tool_call.function.name,
                                     "content": json.dumps(res)})
                else:
                    print("❌ MCP error:", r.text)
            except Exception as e:
                print(f"❌ Error querying time entries: {e}")
                
        elif tool_call.function.name == "log_time_entry_by_name":
            # Show confirmation screen for time entry creation
            # Fetch actual names and IDs for confirmation
            try:
                # Get user details
                user_response = requests.get(f"http://localhost:8000/lookup/user/{args.get('user_name', '')}", timeout=10)
                user_data = user_response.json() if user_response.ok else {"user_id": "N/A", "name": args.get('user_name', 'N/A')}
                
                # Get project details
                project_response = requests.get(f"http://localhost:8000/lookup/workspace/{args.get('project_name', '')}", timeout=10)
                project_data = project_response.json() if project_response.ok else {"workspace_id": "N/A", "name": args.get('project_name', 'N/A')}
                
                # Get task details if provided
                task_data = None
                if args.get('task_name'):
                    task_response = requests.get(f"http://localhost:8000/lookup/story/{project_data.get('workspace_id', 'N/A')}/{args.get('task_name', '')}", timeout=10)
                    task_data = task_response.json() if task_response.ok else {"story_id": "N/A", "name": args.get('task_name', 'N/A')}
                
                # Resolve the actual date
                date_response = requests.post("http://localhost:8000/resolve_date", json={"date": args.get('date', 'today')}, timeout=10)
                resolved_date = date_response.json().get('resolved_date', args.get('date', 'N/A')) if date_response.ok else args.get('date', 'N/A')
                
                print("\n" + "="*60)
                print("📋 TIME ENTRY CONFIRMATION")
                print("="*60)
                print(f"👤 User: {user_data.get('name', args.get('user_name', 'N/A'))} [{user_data.get('user_id', 'N/A')}]")
                print(f"📁 Project: {project_data.get('name', args.get('project_name', 'N/A'))} [{project_data.get('workspace_id', 'N/A')}]")
                if task_data:
                    print(f"📋 Task: {task_data.get('name', args.get('task_name', 'N/A'))} [{task_data.get('story_id', 'N/A')}]")
                print(f"⏱️  Hours: {args.get('hours', 'N/A')}")
                print(f"💰 Billable: {'Yes' if args.get('billable') else 'No'}")
                print(f"📅 Date: {resolved_date}")
                print(f"📝 Notes: {args.get('notes', 'N/A')}")
                print("="*60)
                print("Please confirm this time entry:")
                print("• Type 'yes', 'y', 'confirm' to proceed")
                print("• Type 'no', 'n', 'cancel' to cancel")
                print("• Type corrections (e.g., 'change hours to 2' or 'user should be Sarah')")
                print("="*60)
            except Exception as e:
                print(f"⚠️  Warning: Could not fetch details for confirmation: {e}")
                # Fallback to basic confirmation
                print("\n" + "="*60)
                print("📋 TIME ENTRY CONFIRMATION")
                print("="*60)
                print(f"👤 User: {args.get('user_name', 'N/A')}")
                print(f"📁 Project: {args.get('project_name', 'N/A')}")
                if args.get('task_name'):
                    print(f"📋 Task: {args.get('task_name')}")
                print(f"⏱️  Hours: {args.get('hours', 'N/A')}")
                print(f"💰 Billable: {'Yes' if args.get('billable') else 'No'}")
                print(f"📅 Date: {args.get('date', 'N/A')}")
                print(f"📝 Notes: {args.get('notes', 'N/A')}")
                print("="*60)
                print("Please confirm this time entry:")
                print("• Type 'yes', 'y', 'confirm' to proceed")
                print("• Type 'no', 'n', 'cancel' to cancel")
                print("• Type corrections (e.g., 'change hours to 2' or 'user should be Sarah')")
                print("="*60)
        else:
            # Show confirmation screen for other time entry creation methods
            print("\n" + "="*60)
            print("📋 TIME ENTRY CONFIRMATION")
            print("="*60)
            print(f"👤 User ID: {args.get('user_id', 'N/A')}")
            print(f"📁 Project ID: {args.get('project_id', 'N/A')}")
            if args.get('task_id'):
                print(f"📋 Task ID: {args.get('task_id')}")
            print(f"⏱️  Hours: {args.get('hours', 'N/A')}")
            print(f"💰 Billable: {'Yes' if args.get('billable') else 'No'}")
            print(f"📅 Date: {args.get('date', 'N/A')}")
            print(f"📝 Notes: {args.get('notes', 'N/A')}")
            print("="*60)
            print("Please confirm this time entry:")
            print("• Type 'yes', 'y', 'confirm' to proceed")
            print("• Type 'no', 'n', 'cancel' to cancel")
            print("• Type corrections (e.g., 'change hours to 2' or 'user should be 12345')")
            print("="*60)
        
        # Get user confirmation only for time entry creation, not for queries
        if tool_call.function.name != "query_time_entries":
            confirmation = input("Your response: ").strip().lower()
            
            if confirmation in ['yes', 'y', 'confirm', 'ok', 'proceed', 'yup', 'yeah', 'sure', 'go ahead']:
                # Proceed with the time entry
                if tool_call.function.name == "log_time_entry_by_name":
                    endpoint = "http://localhost:8000/time_entry_by_name"
                else:
                    endpoint = MCP_URL
                    
                r = requests.post(endpoint, json=args, timeout=10)
                if r.ok:
                    res = r.json()
                    if tool_call.function.name == "log_time_entry_by_name":
                        task_info = f"task '{res['task_name']}' " if res['task_name'] else ""
                        print(f"✅ Logged {res['minutes']} min "
                              f"on {res['date']} for {res['user_name']} "
                              f"on project '{res['project_name']}' "
                              f"{task_info}"
                              f"(entry #{res['entry_id']})")
                    else:
                        print(f"✅ Logged {res['minutes']} min "
                              f"on {res['date']} for user {res['user_id']} "
                              f"(entry #{res['entry_id']})")
                    messages.append({"role":"tool",
                                     "tool_call_id": tool_call.id,
                                     "name": tool_call.function.name,
                                     "content": json.dumps(res)})
                else:
                    print("❌ MCP error:", r.text)
            elif confirmation in ['no', 'n', 'cancel', 'abort', 'stop']:
                print("❌ Time entry cancelled.")
            else:
                # Handle corrections - restart the conversation to avoid state corruption
                print(f"🔄 Processing correction: '{confirmation}'")
                # Clear the conversation and start fresh with the correction
                messages.clear()
                messages.append({"role":"system",
                               "content":"You are an assistant that logs time to Kantata OX. When users mention 'today', 'today's date', or similar phrases, always use 'today' as the date parameter. When no specific date is mentioned, default to 'today'. Always extract the date parameter from the user's request and include it in the function call."})
                correction_msg = f"Please correct the time entry: {confirmation}"
                chat(correction_msg)
    else:
        print(msg.content)

if __name__ == "__main__":
    try:
        while True:
            chat(input("You: "))
    except (EOFError, KeyboardInterrupt):
        sys.exit()
