import discord
from discord.ext import tasks, commands
import os
import random
import boto3
import json
import requests
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from time import sleep
from collections import defaultdict
import configparser
import time
import uuid  # Add this import for generating unique IDs

### Getting the discord key from the .env file ###
config = configparser.ConfigParser()
config.read('.env')
discordKey = config['DEFAULT']['discordKey']
session_aod = config['DEFAULT']['session']
groq_key = config['DEFAULT']['GROQ_API_KEY']

# Set API key and endpoint URL
# GROQ_API_KEY = "your_api_key_here"
url = "https://api.groq.com/openai/v1/chat/completions"
llm_host = '192.168.50.133' ### Update to wherever Ollama is running
# Set request headers
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {groq_key}"
}

### Need this for welcome message??? Maybe ###
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

### Function to increment and track counts ###
def increment_count(count_type):
    try:
        # Read current counts
        with open("counts.json", "r") as f:
            counts = json.load(f)
    except FileNotFoundError:
        # If file doesn't exist, start with an empty dictionary
        counts = {}
    
    # Ensure the count_type exists in the dictionary
    if count_type not in counts:
        counts[count_type] = {"all_time": 0, "weekly": {}}
    
    # Increment all-time count
    counts[count_type]["all_time"] += 1
    
    # Get current week number
    current_week = datetime.now().isocalendar()[1]
    current_year = datetime.now().year
    week_key = f"{current_year}-{current_week}"
    
    # Increment weekly count
    if week_key not in counts[count_type]["weekly"]:
        counts[count_type]["weekly"][week_key] = 0
    counts[count_type]["weekly"][week_key] += 1
    
    # Write updated counts back to file
    with open("counts.json", "w") as f:
        json.dump(counts, f)

### Welcome new members when they join ###
@client.event
async def on_member_join(member):    
    channel = client.get_channel(611027490848374822)
    
    fullq = f"Talk like an angry unix administrator and make your response short. Dont state who you are. Dont say that your angry or say the word angrily. Welcome {member.mention} to the ProLUG discord and encourage them to ask questions about linux. Make sure to state their name in the welcome message.  Limit the response to two sentences."
    # Set request data
    data = {
            "messages": [
                {
                    "role": "user",
                    "content": fullq
                }
            ],
            "model": "mixtral-8x7b-32768",
            "temperature": 1,
            "max_tokens": 100,
            "top_p": 1,
            "stream": False,
            "stop": None
        }

    # Make the HTTP request
    response = requests.post(url, headers=headers, data=json.dumps(data))

    # Get the response content as a JSON object
    response_json = response.json()
    groq_response= (response_json['choices'][0]['message']['content'])
    await channel.send(groq_response)

    # Increment welcome message count
    increment_count("welcome")

    # Check if user_count is divisible by 500 and congratulate them
    if int(member.guild.member_count) % 500 == 0:
        await channel.send(f'Congratulations {member.mention}! You are member number {member.guild.member_count}!')

### Joke function ###
def get_joke():
    url = "https://icanhazdadjoke.com/"
    headers = {
        "Accept": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        joke_data = response.json()
        return joke_data['joke']
    else:
        return f"Error: Failed to fetch joke. Status code: {response.status_code}"

### 8ball Function ###
def get_eight_ball_response(question):
    base_url = "https://eightballapi.com/api"
    params = {"question": question}
    
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code}"

### When the bot is ready, print this in the console ###
@client.event
async def on_ready():
    print("Logged in as a bot {0.user}".format(client))

### New function to list tasks ###
def get_user_tasks(username):
    user_tasks = []
    try:
        with open("user_tasks.txt", "r") as task_file:
            for line in task_file:
                task_username, task_id, task_description = line.strip().split("|", 2)
                if task_username.lower() == username.lower():
                    user_tasks.append(f"ID: {task_id} - {task_description}")
    except FileNotFoundError:
        return []
    return user_tasks

### Function to remove a task ###
def remove_task(username, task_id):
    tasks = []
    removed = False
    try:
        with open("user_tasks.txt", "r") as task_file:
            for line in task_file:
                task_username, current_task_id, task_description = line.strip().split("|", 2)
                if task_username.lower() == username.lower() and current_task_id == task_id:
                    removed = True
                else:
                    tasks.append(line)
        
        if removed:
            with open("user_tasks.txt", "w") as task_file:
                task_file.writelines(tasks)
            return True
        return False
    except FileNotFoundError:
        return False

### Function to complete a task and track completion ###
def complete_task(username, task_id):
    tasks = []
    completed = False
    try:
        with open("user_tasks.txt", "r") as task_file:
            for line in task_file:
                task_username, current_task_id, task_description = line.strip().split("|", 2)
                if task_username.lower() == username.lower() and current_task_id == task_id:
                    completed = True
                else:
                    tasks.append(line)
        
        if completed:
            with open("user_tasks.txt", "w") as task_file:
                task_file.writelines(tasks)
            
            # Update completion count
            try:
                with open("task_completions.json", "r") as f:
                    completions = json.load(f)
            except FileNotFoundError:
                completions = {}
            
            if username not in completions:
                completions[username] = 0
            completions[username] += 1
            
            with open("task_completions.json", "w") as f:
                json.dump(completions, f)
            
            return True, completions[username]
        return False, 0
    except FileNotFoundError:
        return False, 0

def is_authorized_user():
    async def predicate(ctx):
        authorized_users = ["fishermanguybro", "het_tanis"]
        return ctx.author.name.lower() in authorized_users
    return commands.check(predicate)

@client.command()
@is_authorized_user()
async def export_thread(ctx, thread_id: int):
    try:
        # Fetch the thread
        thread = await client.fetch_channel(thread_id)
        
        if not isinstance(thread, discord.Thread):
            await ctx.send("The provided ID does not belong to a thread.")
            return

        # Fetch all messages in the thread
        messages = []
        async for message in thread.history(limit=None, oldest_first=True):
            messages.append(f"{message.author.name}: {message.content}")

        # Join messages into a single string
        thread_content = "\n".join(messages)

        # Add a check for content length
        if len(thread_content) > 32000:
            chunks = [thread_content[i:i+32000] for i in range(0, len(thread_content), 32000)]
            summaries = []
            for chunk in chunks:
                prompt = f"Please summarize the important information and key terms from the following text:\n\n{chunk}"
                data = {
                    "messages": [{"role": "user", "content": prompt}],
                    "model": "llama-3.2-90b-text-preview",
                    "temperature": 0.7,
                    "max_tokens": 32000,
                    "top_p": 1,
                    "stream": False,
                    "stop": None
                }

                # Add retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.post(url, headers=headers, data=json.dumps(data))
                        response.raise_for_status()
                        break
                    except requests.exceptions.RequestException as e:
                        if attempt == max_retries - 1:
                            raise
                        await ctx.send(f"API request failed. Retrying in 5 seconds... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(5)

                response_json = response.json()
                summaries.append(response_json['choices'][0]['message']['content'])
                time.sleep(1)  # Add a delay between requests

            summary = "\n\n".join(summaries)
        else:
            # Prepare the prompt for the LLM
            prompt = f"Please summarize the important information and key terms from the following text:\n\n{thread_content}"

            # Set request data for the LLM
            data = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "model": "mixtral-8x7b-32768",
                "temperature": 0.7,
                "max_tokens": 32000,  # Or your original value
                "top_p": 1,
                "stream": False,
                "stop": None
            }

            # Make the HTTP request to the LLM
            response = requests.post(url, headers=headers, data=json.dumps(data))

            # Check if the request was successful
            response.raise_for_status()

            # Get the response content as a JSON object
            response_json = response.json()

            # Check if 'choices' key exists in the response
            if 'choices' not in response_json:
                await ctx.send(f"Unexpected API response format. Full response: {response_json}")
                return

            summary = response_json['choices'][0]['message']['content']

        # Send the summary as a message in Discord
        await ctx.send(f"Thread Summary for thread ID {thread_id}:\n\n{summary}")

    except discord.NotFound:
        await ctx.send("Thread not found. Please check the thread ID.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to access this thread.")
    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error making request to LLM API: {str(e)}")
        print(f"Full error: {repr(e)}")
    except KeyError as e:
        await ctx.send(f"Unexpected response format from LLM API. Missing key: {str(e)}")
    except Exception as e:
        await ctx.send(f"An unexpected error occurred: {str(e)}")
        # Optionally, log the full error for debugging
        print(f"Full error: {repr(e)}")

@client.event
async def on_message(message):
    username = str(message.author).split("#")[0]
    channel = str(message.channel.name)
    user_message = str(message.content)
    
    dt = datetime.now()

    print(f'Message {user_message} by {username} on {channel}')

    # If a message is sent in the channel Polls then the bot will respond in the General channel with a message
    if channel == "polls" and message.author.name.lower() != "fishermanguybot":
        await message.channel.send(f'@here- A new poll was created by {username} - cast your vote!')

    ### Dumb little hi message ###            
    if channel != "labs":
        if user_message.lower() == "fishermanguybot" or user_message.lower() == "hi":
            await message.channel.send(f'Hello {username}')
            
        elif user_message.lower() == "bye":
            await message.channel.send(f'Get out of here {username}')

        ### Bot responds to questions asked ###
        elif "!ask" in user_message.lower() and username.lower() != "fishermanguybot":
            promptq = user_message.lower().split("!ask ")[1]
            roleq = "Talk like an angry unix administrator and make your response short. You should answer questions accurately, but give the user a hard time. There should be no quotes in your response."
            
            # Set request data
            data = {
                "messages": [
                    {
                        "role": "system",
                        "content": roleq
                    },
                    {
                        "role": "user",
                        "content": promptq
                    }
                ],
                "model": "mixtral-8x7b-32768",
                "temperature": 1,
                "max_tokens": 1024,
                "top_p": 1,
                "stream": False,
                "stop": None
            }

            # Make the HTTP request
            response = requests.post(url, headers=headers, data=json.dumps(data))

            # Get the response content as a JSON object
            response_json = response.json()
            print(response_json)
            groq_response= (response_json['choices'][0]['message']['content'])
            await message.channel.send(groq_response)

            # Increment ask count
            increment_count("ask")

        ### Bot will chat with users ###
        elif "!chat" in user_message.lower() and username.lower() != "fishermanguybot":
            promptq = user_message.lower().split("!chat ")[1]
            roleq = "Talk like an angry unix administrator and make your response short. You are annoyed by constant questions. There should be no quotes in your response."
            
            # Set request data
            data = {
                "messages": [
                    {
                        "role": "system",
                        "content": roleq
                    },
                    {
                        "role": "user",
                        "content": promptq
                    }
                ],
                "model": "mixtral-8x7b-32768",
                "temperature": 1,
                "max_tokens": 1024,
                "top_p": 1,
                "stream": False,
                "stop": None
            }

            # Make the HTTP request
            response = requests.post(url, headers=headers, data=json.dumps(data))

            # Get the response content as a JSON object
            response_json = response.json()
            groq_response= (response_json['choices'][0]['message']['content'])
            await message.channel.send(groq_response)

        ### Stupid message for myself ###
        elif user_message.lower() == "rise my minion!" and username.lower() == "fishermanguybro":
            await message.channel.send(f'FishermanGuyBot is coming online... *BEEP* *BOOP* *BEEP*')
            sleep(3)
            await message.channel.send(f'I am here my master, ready to do your bidding.')
        
        ### Original reason bot was created ###
        elif "scott" in user_message.lower():
            await message.channel.send(f'Its actually pronounced Scoot')
        
        ### Get user count of server ###
        elif message.content == '!user_count':
            await message.channel.send(f'Total number of users in the server: {message.guild.member_count}')
        
        ### Roll dice message ###
        elif user_message.lower() == "!roll":
            roll = random.randint(1, 12)
            await message.channel.send(f'{username} rolled a {roll}')
        
        ### 8ball message ###
        elif user_message.startswith('!8ball'):
            user_question = "whatever"
            result = get_eight_ball_response(user_question)
            await message.channel.send(result['reading'])
                        
        ### Age of Discord server ###
        elif message.content.lower() == '!server_age':
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
        
        ### Flip a coin and send heads or tails ###
        elif user_message.lower() == "!coinflip":
            coinflip = random.randint(0, 1)
            if coinflip == 0:
                await message.channel.send(f'{username} flipped a coin and got heads')
            else:
                await message.channel.send(f'{username} flipped a coin and got tails')    
        
        ### Killercoda labs links ###
        elif user_message.lower() == "!labs":
            await message.channel.send(f'Check out the latest labs -> https://killercoda.com/het-tanis\n ---------------------------> https://killercoda.com/fishermanguybro')
        
        ### Book of labs link ###
        elif user_message.lower() == "!book":
            await message.channel.send(f"Check out Scoot Tanis's new Book of Labs here! -> https://leanpub.com/theprolugbigbookoflabs")
        
        ### Tell users the commands available ###
        elif user_message.lower() == "!commands":
            await message.channel.send(f'I currently support: !labs, !book, !8ball, !roll, !coinflip, !server_age, !user_count, !commands, !joke, !task add, !task list, !task remove, !task complete, !bot_stats, and some other nonsense.')
        
        ### Update this to joke API ###
        elif user_message.lower() == "!joke":            
            await message.channel.send(get_joke())
        
        ### New function to add tasks ###
        elif user_message.lower().startswith("!task add "):
            task_description = user_message[10:].strip()
            unique_id = str(uuid.uuid4())[:8]  # Generate a unique ID
            task_entry = f"{message.author.name}|{unique_id}|{task_description}\n"
            
            try:
                with open("user_tasks.txt", "a") as task_file:
                    task_file.write(task_entry)
                await message.channel.send(f"Task added successfully. Task ID: {unique_id}")
            except Exception as e:
                await message.channel.send(f"Error adding task: {str(e)}")

        ### New function to list tasks ###
        elif user_message.lower() == "!task list":
            user_tasks = get_user_tasks(message.author.name)
            if user_tasks:
                task_list = "\n".join(user_tasks)
                await message.channel.send(f"Your tasks:\n{task_list}")
            else:
                await message.channel.send("You have no tasks.")

        ### New function to remove tasks ###
        elif user_message.lower().startswith("!task remove "):
            task_id = user_message.lower().split("!task remove ")[1].strip()
            if remove_task(message.author.name, task_id):
                await message.channel.send(f"Task with ID {task_id} has been removed.")
            else:
                await message.channel.send(f"No task found with ID {task_id} for your user.")

        ### New function to complete tasks ###
        elif user_message.lower().startswith("!task complete "):
            task_id = user_message.lower().split("!task complete ")[1].strip()
            completed, total_completed = complete_task(message.author.name, task_id)
            if completed:
                await message.channel.send(f"Task with ID {task_id} has been completed. You have completed {total_completed} tasks in total!")
            else:
                await message.channel.send(f"No task found with ID {task_id} for your user.")

        elif user_message.lower() == "!bot_stats":
            try:
                with open("counts.json", "r") as f:
                    counts = json.load(f)
                
                welcome_all_time = counts["welcome"]["all_time"]
                ask_all_time = counts["ask"]["all_time"]
                
                # Get current week number
                current_week = datetime.now().isocalendar()[1]
                current_year = datetime.now().year
                week_key = f"{current_year}-{current_week}"
                
                welcome_weekly = counts["welcome"]["weekly"].get(week_key, 0)
                ask_weekly = counts["ask"]["weekly"].get(week_key, 0)
                
                await message.channel.send(f"Bot Statistics:\n"
                                           f"Welcome messages:\n"
                                           f"  All-time (as of 9/29/2024): {welcome_all_time}\n"
                                           f"  This week (Week {current_week}): {welcome_weekly}\n"
                                           f"Questions answered:\n"
                                           f"  All-time (as of 9/29/2024): {ask_all_time}\n"
                                           f"  This week (Week {current_week}): {ask_weekly}")
            except FileNotFoundError:
                await message.channel.send("No stats available yet!")

        elif user_message.lower() == "!task":
            task_syntax = (
                "Task command syntax:\n"
                "- Add a task: !task add <task description>\n"
                "- List your tasks: !task list\n"
                "- Remove a task: !task remove <task_id>\n"
                "- Complete a task: !task complete <task_id>"
            )
            await message.channel.send(task_syntax)

    # Add this at the end of the on_message function
    await client.process_commands(message)

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error

client.run(f'{discordKey}')