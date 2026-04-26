import discord
from discord.ext import commands, tasks
import asyncio
import logging
from datetime import datetime, time
import pytz

# Local imports
from config import Config, WELCOME_CHANNEL_ID
from api_client import APIClient
from commands import BotCommands, is_authorized_user
from utils import increment_count
from chat_logger import ChatLogger
from weekly_report import WeeklyReport

logger = logging.getLogger(__name__)

class ProLUGBot:
    def __init__(self):
        self.config = Config()
        self.api_client = APIClient(self.config.groq_key, self.config.perplexity_api_key)
        self.bot_commands = BotCommands(self.api_client)
        self.chat_logger = ChatLogger()
        self.weekly_report = WeeklyReport()

        # Setup Discord bot
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        self.client = commands.Bot(command_prefix='!', intents=intents)

        # Override close() to clean up the API session on shutdown
        original_close = self.client.close
        api_client = self.api_client
        async def _close_with_cleanup():
            logger.info("Bot shutting down, closing API session")
            await api_client.close()
            await original_close()
        self.client.close = _close_with_cleanup

        self._setup_scheduled_tasks()
        self._setup_events()
        self._setup_commands()
    
    def _setup_events(self):
        """Setup Discord event handlers."""
        
        @self.client.event
        async def on_ready():
            logger.info("Logged in as a bot %s", self.client.user)
            # Start scheduled tasks after bot is ready
            if not self.send_weekly_report.is_running():
                self.send_weekly_report.start()

        @self.client.event
        async def on_member_join(member):
            channel = self.client.get_channel(WELCOME_CHANNEL_ID)
            if not channel:
                logger.warning("Welcome channel %s not found", WELCOME_CHANNEL_ID)
                return
            
            prompt = f"Talk like an angry unix administrator and make your response short. Welcome {member.mention} to the ProLUG discord and encourage them to ask questions about linux. Make sure to state their name in the welcome message. Limit the response to two sentences."
            
            messages = [
                {"role": "system", "content": "You are a grumpy unix administrator who welcomes new users to a Linux discord server."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.api_client.make_groq_request(messages)
            
            logger.debug("Welcome API response: %s", response)
            logger.debug("Welcome API response length: %s", len(response) if response else 0)
            
            if response and len(response) >= 10:
                await channel.send(response)
                logger.info("Sent welcome message to %s", member.name)
            else:
                default_message = f"Welcome, {member.mention}! Feel free to look around and ask any questions."
                await channel.send(default_message)
                logger.warning("Sent default welcome to %s - API response was: %s", member.name, response)
            
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
            
            logger.debug('Message "%s" by %s on %s', content, username, channel_name)
            
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
            if isinstance(error, commands.CheckFailure):
                return
            logger.error("Command error: %s", error, exc_info=True)
    
    def _setup_commands(self):
        """Setup Discord slash commands."""

        @self.client.command()
        @is_authorized_user()
        async def weekly_report(ctx):
            """Generate and send the weekly report (authorized users only)."""
            await ctx.send("Generating weekly report...")

            # Get statistics
            stats = self.weekly_report.get_weekly_stats()

            if stats:
                # Use AI to get better topic analysis if there are messages
                if stats['total_messages'] > 0 and stats['all_messages']:
                    ai_topic = await self.weekly_report.generate_report_with_ai(
                        self.api_client,
                        stats['all_messages']
                    )
                    if ai_topic:
                        stats['most_discussed_topic'] = ai_topic

                # Format the report
                report = self.weekly_report.format_report(stats)
                await ctx.send(report)
            else:
                await ctx.send("Failed to generate weekly report statistics.")
    
    async def _route_message(self, message: discord.Message) -> None:
        """Route messages to appropriate command handlers."""
        content = message.content.lower()

        # Command routing
        if content.startswith("!ask "):
            await self.bot_commands.handle_ask_command(message)
        elif content.startswith("!chat "):
            await self.bot_commands.handle_chat_command(message)
        elif content.startswith("!addkey "):
            await self.bot_commands.handle_addkey_command(message)
        elif content == "!removekey":
            await self.bot_commands.handle_removekey_command(message)
        elif content == "!keystatus":
            await self.bot_commands.handle_keystatus_command(message)
        elif content in ["!roll", "!user_count", "!server_age", "!coinflip", "!labs",
                        "!book", "!commands", "!joke", "!bot_stats"] or content.startswith("!8ball"):
            await self.bot_commands.handle_simple_commands(message)
        else:
            await self.bot_commands.handle_special_messages(message)

    def _setup_scheduled_tasks(self):
        """Setup scheduled tasks like weekly reports."""

        @tasks.loop(time=time(hour=12, minute=0, tzinfo=pytz.timezone('US/Eastern')))
        async def send_weekly_report():
            """Send weekly report every Sunday at noon EST."""
            # Check if today is Sunday (weekday 6)
            if datetime.now(pytz.timezone('US/Eastern')).weekday() != 6:
                return

            logger.info("Generating scheduled weekly report")

            # Get statistics
            stats = self.weekly_report.get_weekly_stats()

            if stats:
                # Use AI to get better topic analysis if there are messages
                if stats['total_messages'] > 0 and stats['all_messages']:
                    ai_topic = await self.weekly_report.generate_report_with_ai(
                        self.api_client,
                        stats['all_messages']
                    )
                    if ai_topic:
                        stats['most_discussed_topic'] = ai_topic

                # Format the report
                report = self.weekly_report.format_report(stats)

                # Find the "general" channel (case insensitive)
                general_channel = None
                for guild in self.client.guilds:
                    for channel in guild.text_channels:
                        if channel.name.lower() == "general":
                            general_channel = channel
                            break
                    if general_channel:
                        break

                if general_channel:
                    await general_channel.send(report)
                    logger.info("Weekly report sent to #%s", general_channel.name)
                else:
                    logger.error("Could not find 'general' channel to send weekly report")
            else:
                logger.error("Failed to generate weekly report statistics")

        @send_weekly_report.before_loop
        async def before_weekly_report():
            """Wait until the bot is ready before starting the scheduled task."""
            await self.client.wait_until_ready()

        # Store the task as an instance variable (will be started in on_ready)
        self.send_weekly_report = send_weekly_report
    
    def run(self):
        """Start the bot."""
        try:
            self.client.run(self.config.discord_key)
        except Exception as e:
            logger.critical("Failed to start bot", exc_info=True)
            raise

if __name__ == "__main__":
    from logger_setup import setup_logging
    setup_logging()
    bot = ProLUGBot()
    bot.run()