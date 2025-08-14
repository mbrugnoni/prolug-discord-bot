import json
import asyncio
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from config import COUNTS_FILE, TASKS_FILE, COMPLETIONS_FILE

def increment_count(count_type: str) -> None:
    """Increment and track counts for bot statistics."""
    try:
        with open(COUNTS_FILE, "r") as f:
            counts = json.load(f)
    except FileNotFoundError:
        counts = {}
    
    if count_type not in counts:
        counts[count_type] = {"all_time": 0, "weekly": {}}
    
    counts[count_type]["all_time"] += 1
    
    now = datetime.now()
    current_week = now.isocalendar()[1]
    current_year = now.year
    week_key = f"{current_year}-{current_week}"
    
    if week_key not in counts[count_type]["weekly"]:
        counts[count_type]["weekly"][week_key] = 0
    counts[count_type]["weekly"][week_key] += 1
    
    try:
        with open(COUNTS_FILE, "w") as f:
            json.dump(counts, f)
    except IOError as e:
        print(f"Error writing counts file: {e}")

def get_user_tasks(username: str) -> List[str]:
    """Get all tasks for a specific user."""
    user_tasks = []
    try:
        with open(TASKS_FILE, "r") as task_file:
            for line in task_file:
                try:
                    parts = line.strip().split("|", 2)
                    if len(parts) != 3:
                        continue
                    task_username, task_id, task_description = parts
                    if task_username.lower() == username.lower():
                        user_tasks.append(f"ID: {task_id} - {task_description}")
                except ValueError:
                    continue
    except FileNotFoundError:
        return []
    return user_tasks

def remove_task(username: str, task_id: str) -> bool:
    """Remove a task for a specific user."""
    tasks = []
    removed = False
    try:
        with open(TASKS_FILE, "r") as task_file:
            for line in task_file:
                try:
                    parts = line.strip().split("|", 2)
                    if len(parts) != 3:
                        tasks.append(line)
                        continue
                    task_username, current_task_id, task_description = parts
                    if task_username.lower() == username.lower() and current_task_id == task_id:
                        removed = True
                    else:
                        tasks.append(line)
                except ValueError:
                    tasks.append(line)
        
        if removed:
            with open(TASKS_FILE, "w") as task_file:
                task_file.writelines(tasks)
            return True
        return False
    except FileNotFoundError:
        return False

def complete_task(username: str, task_id: str) -> Tuple[bool, int]:
    """Complete a task and track completion count."""
    tasks = []
    completed = False
    try:
        with open(TASKS_FILE, "r") as task_file:
            for line in task_file:
                try:
                    parts = line.strip().split("|", 2)
                    if len(parts) != 3:
                        tasks.append(line)
                        continue
                    task_username, current_task_id, task_description = parts
                    if task_username.lower() == username.lower() and current_task_id == task_id:
                        completed = True
                    else:
                        tasks.append(line)
                except ValueError:
                    tasks.append(line)
        
        if completed:
            with open(TASKS_FILE, "w") as task_file:
                task_file.writelines(tasks)
            
            total_completed = update_completion_count(username)
            return True, total_completed
        return False, 0
    except FileNotFoundError:
        return False, 0

def update_completion_count(username: str) -> int:
    """Update and return the completion count for a user."""
    try:
        with open(COMPLETIONS_FILE, "r") as f:
            completions = json.load(f)
    except FileNotFoundError:
        completions = {}
    
    if username not in completions:
        completions[username] = 0
    completions[username] += 1
    
    try:
        with open(COMPLETIONS_FILE, "w") as f:
            json.dump(completions, f)
    except IOError as e:
        print(f"Error writing completions file: {e}")
    
    return completions[username]

def get_bot_stats() -> Optional[Dict]:
    """Get bot statistics from counts file."""
    try:
        with open(COUNTS_FILE, "r") as f:
            counts = json.load(f)
        
        now = datetime.now()
        current_week = now.isocalendar()[1]
        current_year = now.year
        week_key = f"{current_year}-{current_week}"
        
        return {
            "welcome_all_time": counts.get("welcome", {}).get("all_time", 0),
            "ask_all_time": counts.get("ask", {}).get("all_time", 0),
            "welcome_weekly": counts.get("welcome", {}).get("weekly", {}).get(week_key, 0),
            "ask_weekly": counts.get("ask", {}).get("weekly", {}).get(week_key, 0),
            "current_week": current_week
        }
    except FileNotFoundError:
        return None

def parse_command_args(message: str, command: str) -> Optional[str]:
    """Safely parse command arguments from message."""
    parts = message.lower().split(f"{command} ", 1)
    if len(parts) < 2:
        return None
    return parts[1].strip()