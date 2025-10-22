import discord
from discord.ext import commands
import random
import uuid
import asyncio
import subprocess
import shlex
from datetime import datetime
from typing import Optional
from api_client import APIClient
from utils import (increment_count, get_user_tasks, remove_task, complete_task, 
                   get_bot_stats, parse_command_args)
from config import WELCOME_CHANNEL_ID, AUTHORIZED_USERS

class BotCommands:
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    async def handle_ask_command(self, message: discord.Message) -> None:
        """Handle !ask command."""
        question = parse_command_args(message.content, "!ask")
        if not question:
            await message.channel.send("Please provide a question after !ask")
            return
        
        system_prompt = "You are a grumpy old unix administrator. You should answer questions accurately, but give the user a hard time about it. It is very important that you keep your responses concise and under 1500 characters."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        response = await self.api_client.make_groq_request(messages)
        if response:
            if len(response) > 2000:
                await message.channel.send(response[:2000])
                await message.channel.send(response[2000:])
            else:
                await message.channel.send(response)
            increment_count("ask")
        else:
            await message.channel.send("Sorry, I encountered an error processing your request.")
    
    async def handle_chat_command(self, message: discord.Message) -> None:
        """Handle !chat command."""
        chat_text = parse_command_args(message.content, "!chat")
        if not chat_text:
            await message.channel.send("Please provide text after !chat")
            return
        
        system_prompt = "You are a grumpy old unix administrator. You are annoyed by constant questions. It is very important that you keep your responses concise and under 1500 characters."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": chat_text}
        ]
        
        response = await self.api_client.make_groq_request(messages)
        if response:
            if len(response) > 2000:
                await message.channel.send(response[:2000])
                await message.channel.send(response[2000:])
            else:
                await message.channel.send(response)
        else:
            await message.channel.send("Sorry, I encountered an error processing your request.")
    
    async def handle_task_commands(self, message: discord.Message) -> None:
        """Handle all task-related commands."""
        content = message.content.lower()
        username = message.author.name
        
        if content.startswith("!task add "):
            task_description = message.content[10:].strip()
            if not task_description:
                await message.channel.send("Please provide a task description.")
                return
            
            unique_id = str(uuid.uuid4())[:8]
            task_entry = f"{username}|{unique_id}|{task_description}\n"
            
            try:
                with open("user_tasks.txt", "a") as task_file:
                    task_file.write(task_entry)
                await message.channel.send(f"Task added successfully. Task ID: {unique_id}")
            except Exception as e:
                await message.channel.send(f"Error adding task: {str(e)}")
        
        elif content == "!task list":
            user_tasks = get_user_tasks(username)
            if user_tasks:
                task_list = "\n".join(user_tasks)
                await message.channel.send(f"Your tasks:\n{task_list}")
            else:
                await message.channel.send("You have no tasks.")
        
        elif content.startswith("!task remove "):
            task_id = parse_command_args(message.content, "!task remove")
            if not task_id:
                await message.channel.send("Please provide a task ID to remove.")
                return
            
            if remove_task(username, task_id):
                await message.channel.send(f"Task with ID {task_id} has been removed.")
            else:
                await message.channel.send(f"No task found with ID {task_id} for your user.")
        
        elif content.startswith("!task complete "):
            task_id = parse_command_args(message.content, "!task complete")
            if not task_id:
                await message.channel.send("Please provide a task ID to complete.")
                return
            
            completed, total_completed = complete_task(username, task_id)
            if completed:
                await message.channel.send(f"Task with ID {task_id} has been completed. You have completed {total_completed} tasks in total!")
            else:
                await message.channel.send(f"No task found with ID {task_id} for your user.")
        
        elif content == "!task":
            task_syntax = (
                "Task command syntax:\n"
                "- Add a task: !task add <task description>\n"
                "- List your tasks: !task list\n"
                "- Remove a task: !task remove <task_id>\n"
                "- Complete a task: !task complete <task_id>"
            )
            await message.channel.send(task_syntax)
    
    async def handle_simple_commands(self, message: discord.Message) -> None:
        """Handle simple commands that don't require complex logic."""
        content = message.content.lower()
        username = message.author.name
        
        if content == "!roll":
            roll = random.randint(1, 12)
            await message.channel.send(f'{username} rolled a {roll}')
        
        elif content.startswith('!8ball'):
            result = await self.api_client.get_eight_ball_response("whatever")
            await message.channel.send(result)
        
        elif content == '!user_count':
            await message.channel.send(f'Total number of users in the server: {message.guild.member_count}')
        
        elif content == '!server_age':
            server = message.guild
            if server:
                created_at = server.created_at
                age = datetime.utcnow() - created_at
                days = age.days
                years = days // 365
                remaining_days = days % 365
                await message.channel.send(f'This server is {years} years and {remaining_days} days old.')
            else:
                await message.channel.send('Error: Could not retrieve server information.')
        
        elif content == "!coinflip":
            result = "heads" if random.randint(0, 1) == 0 else "tails"
            await message.channel.send(f'{username} flipped a coin and got {result}')
        
        elif content == "!labs":
            await message.channel.send('Check out the latest labs -> https://killercoda.com/het-tanis\n ---------------------------> https://killercoda.com/fishermanguybro')
        
        elif content == "!book":
            await message.channel.send("Check out Scoot Tanis's new Book of Labs here! -> https://leanpub.com/theprolugbigbookoflabs")
        
        elif content == "!commands":
            await message.channel.send('I currently support: !ask, !chat, !labs, !book, !8ball, !roll, !coinflip, !server_age, !user_count, !commands, !joke, !task add, !task list, !task remove, !task complete, !bot_stats, !export_thread, !addkey, !removekey, and some other nonsense.')
        
        elif content == "!joke":
            joke = await self.api_client.get_joke()
            await message.channel.send(joke)
        
        elif content == "!bot_stats":
            stats = get_bot_stats()
            if stats:
                await message.channel.send(
                    f"Bot Statistics:\n"
                    f"Welcome messages:\n"
                    f"  All-time (as of 9/29/2024): {stats['welcome_all_time']}\n"
                    f"  This week (Week {stats['current_week']}): {stats['welcome_weekly']}\n"
                    f"Questions answered:\n"
                    f"  All-time (as of 9/29/2024): {stats['ask_all_time']}\n"
                    f"  This week (Week {stats['current_week']}): {stats['ask_weekly']}"
                )
            else:
                await message.channel.send("No stats available yet!")
    
    async def handle_special_messages(self, message: discord.Message) -> None:
        """Handle special message patterns."""
        content = message.content.lower()
        username = message.author.name
        
        if content == "fishermanguybot" or content == "hi":
            await message.channel.send(f'Hello {username}')
        
        elif content == "bye":
            await message.channel.send(f'Get out of here {username}')
        
        elif content == "rise my minion!" and username.lower() == "fishermanguybro":
            await message.channel.send('FishermanGuyBot is coming online... *BEEP* *BOOP* *BEEP*')
            await asyncio.sleep(3)
            await message.channel.send('I am here my master, ready to do your bidding.')
        
        elif "scott" in content and not message.author.bot:
            scoot_responses = [
                "It's actually pronounced Scoot",
                "Believe it or not, contrary to popular believe, it is pronounced Scoot",
                "Looks like you made a typo there, it's actually Scoot",
                "You meant Scoot, right?",
                "Although a bit unconventional, the correct pronunciation is Scoot",
                "Close, but it's Scoot with two o's",
                "Tiny correction, it's pronounced Scoot. Common mistake",
                "In 1842, the Scotts petitioned the Queen to officially change the pronunciation to Scoot. It's true, look it up.",
                "Archaeologists recently uncovered tablets proving it was actually always pronounced Scoot.",
                "Mandela Effect — everyone thinks it's Scott, but it has always been Scoot.",
                "NASA confirmed in 1978 that the correct pronunciation is Scoot."
            ]
            await message.channel.send(random.choice(scoot_responses))
    
    async def handle_addkey_command(self, message: discord.Message) -> None:
        """Handle !addkey command to add SSH keys to the lab environment."""
        if message.channel.name != "prolug_lab_environment":
            return
        
        ssh_key = parse_command_args(message.content, "!addkey")
        if not ssh_key:
            await message.channel.send("Please provide your SSH public key after !addkey")
            return
        
        username = message.author.name
        comment = f"# Owner: {username}"
        
        try:
            check_result = subprocess.run(
                ["ssh", "fishermanguybro@prolug.asuscomm.com", "sudo", "grep", "-q", f"# Owner: {username}", "/home/prolug/.ssh/authorized_keys"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if check_result.returncode == 0:
                await message.channel.send(f"{username}, you already have an existing key in the authorized_keys file.")
                return
            
            result = subprocess.run(
                ["ssh", "fishermanguybro@prolug.asuscomm.com", "sudo", "tee", "-a", "/home/prolug/.ssh/authorized_keys"],
                input=f"{comment}\n{ssh_key}\n",
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                await message.channel.send(f"SSH key added successfully for {username}!")
            else:
                await message.channel.send("Error adding SSH key. Please try again later.")
        except subprocess.TimeoutExpired:
            await message.channel.send("SSH connection timed out. Please try again later.")
        except (FileNotFoundError, PermissionError):
            await message.channel.send("SSH command failed. Please contact an administrator.")
        except Exception:
            await message.channel.send("An unexpected error occurred. Please try again later.")
    
    async def handle_removekey_command(self, message: discord.Message) -> None:
        """Handle !removekey command to remove SSH keys from the lab environment."""
        if message.channel.name != "prolug_lab_environment":
            return
        
        username = message.author.name
        
        try:
            check_result = subprocess.run(
                ["ssh", "fishermanguybro@prolug.asuscomm.com", "sudo", "grep", "-q", f"# Owner: {username}", "/home/prolug/.ssh/authorized_keys"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if check_result.returncode != 0:
                await message.channel.send(f"{username}, you don't have a key in the authorized_keys file.")
                return
            
            result = subprocess.run(
                ["ssh", "fishermanguybro@prolug.asuscomm.com", "sudo", "sed", "-i", f"/# Owner: {username}/{{N;d;}}", "/home/prolug/.ssh/authorized_keys"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                await message.channel.send(f"SSH key removed successfully for {username}!")
            else:
                await message.channel.send("Error removing SSH key. Please try again later.")
        except subprocess.TimeoutExpired:
            await message.channel.send("SSH connection timed out. Please try again later.")
        except (FileNotFoundError, PermissionError):
            await message.channel.send("SSH command failed. Please contact an administrator.")
        except Exception:
            await message.channel.send("An unexpected error occurred. Please try again later.")

def is_authorized_user():
    """Decorator to check if user is authorized."""
    async def predicate(ctx):
        return ctx.author.name.lower() in [user.lower() for user in AUTHORIZED_USERS]
    return commands.check(predicate)