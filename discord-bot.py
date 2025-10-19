import discord
from discord.ext import commands
import asyncio
import uuid
from datetime import datetime

# Local imports
from config import Config, WELCOME_CHANNEL_ID
from api_client import APIClient
from commands import BotCommands, is_authorized_user
from utils import increment_count
from chat_logger import ChatLogger

class ProLUGBot:
    def __init__(self):
        self.config = Config()
        self.api_client = APIClient(self.config.groq_key, self.config.perplexity_api_key)
        self.bot_commands = BotCommands(self.api_client)
        self.chat_logger = ChatLogger()
        
        # Setup Discord bot
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        self.client = commands.Bot(command_prefix='!', intents=intents)
        
        self._setup_events()
        self._setup_commands()
    
    def _setup_events(self):
        """Setup Discord event handlers."""
        
        @self.client.event
        async def on_ready():
            print(f"Logged in as a bot {self.client.user}")
        
        @self.client.event
        async def on_member_join(member):
            channel = self.client.get_channel(WELCOME_CHANNEL_ID)
            if not channel:
                print(f"Warning: Welcome channel {WELCOME_CHANNEL_ID} not found")
                return
            
            prompt = f"Talk like an angry unix administrator and make your response short. Welcome {member.mention} to the ProLUG discord and encourage them to ask questions about linux. Make sure to state their name in the welcome message. Limit the response to two sentences."
            
            messages = [
                {"role": "system", "content": "You are a grumpy unix administrator who welcomes new users to a Linux discord server."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.api_client.make_groq_request(messages)
            
            print(f"API Response: {response}")
            print(f"Response length: {len(response) if response else 0}")
            
            if response and len(response) >= 10:
                await channel.send(response)
                print(f"Sent welcome message to {member.mention}")
            else:
                default_message = f"Welcome, {member.mention}! Feel free to look around and ask any questions."
                await channel.send(default_message)
                print(f"Sent default welcome message to {member.mention} - API response was: {response}")
            
            increment_count("welcome")
            
            # Congratulate milestone members
            if member.guild.member_count % 500 == 0:
                await channel.send(f'🎉🎊 @here - Congratulations {member.mention}! 🎉🎊 You are member number {member.guild.member_count}! 🥳🎈')
        
        @self.client.event
        async def on_message(message):
            # Ignore bot messages
            if message.author == self.client.user:
                return
            
            username = message.author.name
            channel_name = message.channel.name
            content = message.content
            
            # Log the message
            self.chat_logger.log_message(
                user_id=message.author.id,
                username=username,
                channel_id=message.channel.id,
                channel_name=channel_name,
                message_content=content
            )
            
            print(f'Message "{content}" by {username} on {channel_name}')
            
            # Handle polls channel
            if channel_name == "polls" and username.lower() != "fishermanguybot":
                await message.channel.send(f'@here- A new poll was created by {username} - cast your vote!')
            
            # Skip labs channel for most commands
            if channel_name == "labs":
                await self.client.process_commands(message)
                return
            
            # Route messages to appropriate handlers
            await self._route_message(message)
            await self.client.process_commands(message)
        
        @self.client.event
        async def on_command_error(ctx, error):
            if isinstance(error, commands.CommandNotFound):
                return
            print(f"Command error: {error}")
            raise error
    
    def _setup_commands(self):
        """Setup Discord slash commands."""
        
        @self.client.command()
        @is_authorized_user()
        async def export_thread(ctx, thread_id: int):
            """Export and summarize a thread (authorized users only)."""
            try:
                thread = await self.client.fetch_channel(thread_id)
                
                if not isinstance(thread, discord.Thread):
                    await ctx.send("The provided ID does not belong to a thread.")
                    return
                
                # Fetch messages
                messages = []
                async for msg in thread.history(limit=None, oldest_first=True):
                    messages.append(f"{msg.author.name}: {msg.content}")
                
                thread_content = "\n".join(messages)
                prompt = f"Summarize the important information and key terms from the following text:\n\n{thread_content}\n\nSummary:"
                
                summary_messages = [
                    {"role": "system", "content": "You are a helpful assistant that summarizes Discord thread conversations. Be precise and concise."},
                    {"role": "user", "content": prompt}
                ]
                
                summary = await self.api_client.make_perplexity_request(summary_messages)
                
                if summary:
                    # Split into chunks
                    chunks = [summary[i:i+1900] for i in range(0, len(summary), 1900)]
                    
                    await ctx.send(f"Thread Summary for thread ID {thread_id}:")
                    for i, chunk in enumerate(chunks, 1):
                        await ctx.send(f"Part {i}/{len(chunks)}:\n\n{chunk}")
                else:
                    await ctx.send("Failed to generate summary.")
                    
            except discord.NotFound:
                await ctx.send("Thread not found. Please check the thread ID.")
            except discord.Forbidden:
                await ctx.send("I don't have permission to access this thread.")
            except Exception as e:
                await ctx.send(f"An unexpected error occurred: {str(e)}")
                print(f"Export thread error: {e}")
    
    async def _route_message(self, message: discord.Message) -> None:
        """Route messages to appropriate command handlers."""
        content = message.content.lower()
        
        # Command routing
        if content.startswith("!ask "):
            await self.bot_commands.handle_ask_command(message)
        elif content.startswith("!chat "):
            await self.bot_commands.handle_chat_command(message)
        elif content.startswith("!task"):
            await self.bot_commands.handle_task_commands(message)
        elif content.startswith("!addkey "):
            await self.bot_commands.handle_addkey_command(message)
        elif content == "!removekey":
            await self.bot_commands.handle_removekey_command(message)
        elif content in ["!roll", "!user_count", "!server_age", "!coinflip", "!labs", 
                        "!book", "!commands", "!joke", "!bot_stats"] or content.startswith("!8ball"):
            await self.bot_commands.handle_simple_commands(message)
        else:
            await self.bot_commands.handle_special_messages(message)
    
    def run(self):
        """Start the bot."""
        try:
            self.client.run(self.config.discord_key)
        except Exception as e:
            print(f"Failed to start bot: {e}")
            raise

if __name__ == "__main__":
    bot = ProLUGBot()
    bot.run()