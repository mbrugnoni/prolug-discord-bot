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

### Function to increment and track welcome message count ###
def increment_welcome_count():
    try:
        # Read current counts
        with open("counts.json", "r") as f:
            counts = json.load(f)
    except FileNotFoundError:
        # If file doesn't exist, start counts at 0
        counts = {"all_time": 0, "weekly": {}}
    
    # Increment all-time count
    counts["all_time"] += 1
    
    # Get current week number
    current_week = datetime.now().isocalendar()[1]
    current_year = datetime.now().year
    week_key = f"{current_year}-{current_week}"
    
    # Increment weekly count
    if week_key not in counts["weekly"]:
        counts["weekly"][week_key] = 0
    counts["weekly"][week_key] += 1
    
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
    increment_welcome_count()

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
            await message.channel.send(f'I currently support: !labs, !book, !8ball, !roll, !coinflip, !server_age, !user_count, !commands, !joke, !task add, and some other nonsense.')
        
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

        elif user_message.lower() == "!welcome_count":
            try:
                with open("counts.json", "r") as f:
                    counts = json.load(f)
                
                all_time_count = counts["all_time"]
                
                # Get current week number
                current_week = datetime.now().isocalendar()[1]
                current_year = datetime.now().year
                week_key = f"{current_year}-{current_week}"
                
                weekly_count = counts["weekly"].get(week_key, 0)
                
                await message.channel.send(f"I have welcomed {all_time_count} new members in total!\n"
                                       f"This week (Week {current_week}), I've welcomed {weekly_count} new members.")
            except FileNotFoundError:
                await message.channel.send("I haven't welcomed any new members yet!")

client.run(f'{discordKey}')