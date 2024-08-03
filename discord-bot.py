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

### Getting the discord key from the .env file ###
config = configparser.ConfigParser()
config.read('.env')
discordKey = config['DEFAULT']['discordKey']
session_aod = config['DEFAULT']['session']

llm_host = '192.168.50.133' ### Update to wherever Ollama is running


### Need this for welcome message??? Maybe ###
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

### Welcome new members when they join ###
@client.event
async def on_member_join(member):    
    channel = client.get_channel(611027490848374822)
        
    fullq = f"Talk like an angry unix administrator and make your response short. Dont state who you are. Dont say that your angry or say the word angrily. Welcome {member.mention} to the ProLUG discord and encourage them to ask questions about linux. Make sure to state their name in the welcome message. Limit the response to two sentences."
    data = {
            "model": "mistral",
            "prompt": fullq,
            "stream": False
    }
    response = requests.post(f"http://{llm_host}:11434/api/generate", json=data)
    response_data = response.json()
    if response_data['response'].startswith('Angrily:'):
        response_data['response'] = response_data['response'][8:]
    if response_data['response'].startswith('"'):
        response_data['response'] = response_data['response'][1:-1]

    await channel.send(response_data['response'])

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
        elif "!ask" in user_message.lower():
            promptq = user_message.lower().split("!ask ")[1]
            roleq = "Talk like an angry unix administrator and make your response short. Dont state who you are."
            fullq = roleq + promptq
            data = {
                "model": "mistral",
                "prompt": fullq,
                "stream": False
            }
            response = requests.post(f"http://{llm_host}:11434/api/generate", json=data)
            response_data = response.json()            
            await message.channel.send(response_data['response'])

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
            await message.channel.send(f'I currently support: !labs, !book, !8ball, !roll, !coinflip, !server_age, !user_count, !commands, !joke, and some other nonsense.')
        
        ### Update this to joke API ###
        elif user_message.lower() == "!joke":            
            await message.channel.send(get_joke())
        
        # elif user_message.lower() == "!codewars":
        #     url = 'https://www.codewars.com/api/v1/clans/ProLUG/members'

        #     response = requests.get(url)
        #     data = response.json()
        #     json_data = json.dumps(data)
        #     parsed = json.loads(json_data)

        #     rank=1
        #     leaderboard=''
        #     await message.channel.send('Current ProLUG Codewars Leaderboard:')
        #     for member in parsed["data"]:                
        #         leaderboard+=(f'{rank}. {member["username"]} - {member["honor"]}\n')
        #         rank+=1
        #     await message.channel.send(leaderboard)
        #     await message.channel.send(':trophy::trophy::trophy: If you beat FishermanGuyBro, Sending_Grounds or KingBunz by Oct31, you win a Humble Bundle :trophy::trophy::trophy:')

client.run(f'{discordKey}')