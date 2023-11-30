import discord
from discord.ext import tasks, commands
import os
import random
import boto3
import requests
import json
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from time import sleep
from collections import defaultdict
import configparser

config = configparser.ConfigParser()
config.read('.env')
discordKey = config['DEFAULT']['discordKey']

### Trying this out ###
intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix='!', intents=intents)

@client.event
async def on_member_join(member):    
    channel = client.get_channel(611027490848374822)
    welcome_message = f"Welcome {member.mention}! Feel free to look around and ask questions!"
    await channel.send(welcome_message)

@client.event
async def on_ready():
    print("Logged in as a bot {0.user}".format(client))

@client.event
async def on_message(message):
    username = str(message.author).split("#")[0]
    channel = str(message.channel.name)
    user_message = str(message.content)

    # Getting the current date and time
    dt = datetime.now()
  
    print(f'Message {user_message} by {username} on {channel}')

    # If a message is sent in the channel Polls then the bot will respond in the General channel with a message
    if channel == "polls" and message.author.name.lower() != "fishermanguybot":
        await message.channel.send(f'@here- A new poll was created by {username} - cast your vote!')
                
    if channel != "labs":
        if user_message.lower() == "fishermanguybot" or user_message.lower() == "hi":
            await message.channel.send(f'Hello {username}')
            
        elif user_message.lower() == "bye":
            await message.channel.send(f'Get out of here {username}')
        elif user_message.lower() == "!schedule" and (username.lower() == "fishermanguybro" or username.lower() == "het_tanis"):
            # guild_id = client.get_guild(611027490848374811)
            guild_id = '611027490848374811'
            url = f"https://discord.com/api/v10/guilds/{guild_id}/scheduled-events"
            next_saturday = datetime.today()
            while next_saturday.weekday() != 5:
                next_saturday += timedelta(days=1)

            # Set to 6 PM time    
            next_saturday = next_saturday.replace(hour=18, minute=0, second=0) 

            # Convert to UTC   
            eastern = timezone(timedelta(hours=-5))
            next_saturday = next_saturday.astimezone(eastern)

            # Format as ISO8601 string
            scheduled_start_time = next_saturday.isoformat()
            data = {
                "name": "ProLUG Weekly Meeting",
                "description": "Meeting to hang out, talk shop, work on projects.",                
                "scheduled_start_time" : scheduled_start_time,
                "entity_type": 2,
                "entity_metadata": None,
                "channel_id" : "671106405796806675",
                "privacy_level": 2
            }
            print(data)

            headers = {"Authorization": f"Bot {discordKey}","Content-Type": "application/json"}
            r = requests.post(url, headers=headers, json=data)

            response = r.json()
            print(response)

        elif user_message.lower() == "rise my minion!" and username.lower() == "fishermanguybro":
            await message.channel.send(f'FishermanGuyBot is coming online... *BEEP* *BOOP* *BEEP*')
            sleep(3)
            await message.channel.send(f'I am here my master, ready to do your bidding.')
        elif "scott" in user_message.lower():
            await message.channel.send(f'Its actually pronounced Scoot')
        elif message.content == '!user_count':
        #    guild = message.guild
        #    member_count = guild.member_count
        #    await message.channel.send(f'Total number of users in the server: {member_count}')
           await message.channel.send(f'Total number of users in the server: {message.guild.member_count}')
        elif user_message.lower() == "!roll":
            roll = random.randint(1, 12)
            await message.channel.send(f'{username} rolled a {roll}')
        elif user_message.startswith('!8ball'):
            responses = [
                'It is certain.', 
                'It is decidedly so.',
                'Without a doubt.',
                'Yes definitely.',
                'You may rely on it.',
                'As I see it, yes.',
                'Most likely.',
                'Outlook good.',
                'Yes.',
                'Signs point to yes.',
                'Reply hazy, try again.',
                'Ask again later.',
                'Better not tell you now.',
                'Cannot predict now.',
                'Concentrate and ask again.',
                "Don't count on it.",
                'My reply is no.',
                'My sources say no.',
                'Outlook not so good.',
                'Very doubtful.'
            ]
            await message.channel.send(random.choice(responses))
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
        elif user_message.lower() == "!coinflip":
            coinflip = random.randint(0, 1)
            if coinflip == 0:
                await message.channel.send(f'{username} flipped a coin and got heads')
            else:
                await message.channel.send(f'{username} flipped a coin and got tails')    
        elif user_message.lower() == "!labs":
            await message.channel.send(f'Check out the latest labs -> https://killercoda.com/het-tanis')
        elif user_message.lower() == "!book":
            await message.channel.send(f"Check out Scoot Tanis's new Book of Labs here! -> https://leanpub.com/theprolugbigbookoflabs")
        elif user_message.lower() == "!commands":
            await message.channel.send(f'I currently support: !labs, !book, !codewars, !8ball, !roll, !coinflip, !server_age, !user_count, !commands, !joke, and some other nonsense.')
        elif user_message.lower() == "!joke":
            jokes = [" What's on Chris Rock's Face? \nFresh Prints!",
                     "My wife just completed a 40-week bodybuilding program this morning.\nIt's a girl and weighs 7lbs 12 oz.",
                     "Of all the inventions of the last 100 years, the dry erase board has to be the most remarkable.",
                     "Why was 2019 afraid of 2020?\nBecause they had a fight and 2021.",
                     "Did you hear the one about the dog and the tree?\nThey had a long conversation about bark.",
                      "My son was just born and another dad at the nursery congratulated me and said his daughter was born yesterday. He said maybe they'll marry each other.\nSure, like my son is going to marry someone twice his age.",
                      "My landlord texted saying we need to meet up and talk about how high my heating bill is.\nI said, sure! My door is always open!",
                      "It's a 5-minute walk from my house to the bar, but a 45-minute walk from the bar to my house.\nThe difference is staggering.",
                      "To whomever stole my Microsoft Office, I will find you, you have my Word...",
                      "What has five toes but isn’t your foot?\nMy foot.",
                      "Did I ever tell you about the time I was addicted to the hokey pokey? I was, but then I turned myself around.",
                      "What do you call a fly without wings?\nA walk!",
                      "What do sprinters eat before a race?\nNothing. They fast.",
                      "Which knight invented King Arthur's Round Table?\nSir Cumference.",
                      "What do you call a belt made of watches?\nA waist of time!",
                      "I caught my son chewing on electrical cords, so I had to ground him.\nHe’s doing better currently, and now conducting himself properly."]
            await message.channel.send(random.choice(jokes))
        elif user_message.lower() == "!codewars":
            url = 'https://www.codewars.com/api/v1/clans/ProLUG/members'

            response = requests.get(url)
            data = response.json()
            json_data = json.dumps(data)
            parsed = json.loads(json_data)

            rank=1
            leaderboard=''
            await message.channel.send('Current ProLUG Codewars Leaderboard:')
            for member in parsed["data"]:                
                leaderboard+=(f'{rank}. {member["username"]} - {member["honor"]}\n')
                rank+=1
            await message.channel.send(leaderboard)
            await message.channel.send(':trophy::trophy::trophy: If you beat FishermanGuyBro, Sending_Grounds or KingBunz by Oct31, you win a Humble Bundle :trophy::trophy::trophy:')

client.run(f'{discordKey}')