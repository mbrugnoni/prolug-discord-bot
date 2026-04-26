import discord
from discord.ext import commands
import logging
import random
import re
import base64
import asyncio
import shlex
from datetime import datetime, timezone
from typing import Optional
from api_client import APIClient
from utils import increment_count, get_bot_stats, parse_command_args
from config import WELCOME_CHANNEL_ID, AUTHORIZED_USERS

logger = logging.getLogger(__name__)

SSH_HOST = "fishermanguybro@prolug.asuscomm.com"
AUTHORIZED_KEYS_PATH = "/home/prolug/.ssh/authorized_keys"
SSH_TIMEOUT = 10
VALID_SSH_KEY_TYPES = frozenset([
    'ssh-rsa', 'ssh-ed25519', 'ssh-dss',
    'ecdsa-sha2-nistp256', 'ecdsa-sha2-nistp384', 'ecdsa-sha2-nistp521',
])


def _sanitize_username(username: str) -> Optional[str]:
    """Sanitize username for safe use in shell commands.

    Returns the username if it only contains safe characters, or None if it
    contains characters that could be used for shell injection.
    """
    if not username or len(username) > 64:
        return None
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', username):
        return None
    return username


def _validate_ssh_key(key: str) -> bool:
    """Validate that a string looks like a valid SSH public key."""
    parts = key.strip().split()
    if len(parts) < 2:
        return False
    if parts[0] not in VALID_SSH_KEY_TYPES:
        return False
    try:
        base64.b64decode(parts[1], validate=True)
    except Exception:
        return False
    return True


async def _run_ssh_command(cmd: str, input_data: str = None) -> tuple:
    """Run a command on the remote host via SSH asynchronously.

    Returns (returncode, stdout, stderr).
    """
    args = ["ssh", SSH_HOST, cmd]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE if input_data else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(input=input_data.encode() if input_data else None),
        timeout=SSH_TIMEOUT,
    )
    return proc.returncode, stdout.decode(), stderr.decode()


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
                age = datetime.now(timezone.utc) - created_at
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
            await message.channel.send('I currently support: !ask, !chat, !labs, !book, !8ball, !roll, !coinflip, !server_age, !user_count, !commands, !joke, !bot_stats, !addkey, !removekey, !keystatus, and some other nonsense.')

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
        safe_username = _sanitize_username(username)
        if not safe_username:
            logger.warning("Rejected unsafe username for SSH addkey: %s", username)
            await message.channel.send("Your username contains characters that aren't supported. Please contact an administrator for manual key addition.")
            return

        if not _validate_ssh_key(ssh_key):
            await message.channel.send("Invalid SSH key format. Please provide a valid public key (e.g. ssh-ed25519 AAAA...).")
            return

        comment = f"# Owner: {safe_username}"

        try:
            # Check if user already has a key
            returncode, stdout, stderr = await _run_ssh_command(
                f"sudo grep -iF {shlex.quote('# Owner: ' + safe_username)} {AUTHORIZED_KEYS_PATH}"
            )

            if returncode == 0:
                await message.channel.send(f"{username}, you already have an existing key in the authorized_keys file.")
                return

            # Add the new key
            returncode, stdout, stderr = await _run_ssh_command(
                f"sudo tee -a {AUTHORIZED_KEYS_PATH}",
                input_data=f"{comment}\n{ssh_key}\n",
            )

            if returncode == 0:
                await message.channel.send(f"SSH key added successfully for {username}!")
            else:
                logger.error("SSH addkey failed for %s: returncode=%s stderr=%s",
                             username, returncode, stderr)
                await message.channel.send("Error adding SSH key. Please try again later.")
        except asyncio.TimeoutError:
            logger.error("SSH addkey timed out for %s", username)
            await message.channel.send("SSH connection timed out. Please try again later.")
        except Exception:
            logger.error("Unexpected error in SSH addkey for %s", username, exc_info=True)
            await message.channel.send("An unexpected error occurred. Please try again later.")

    async def handle_removekey_command(self, message: discord.Message) -> None:
        """Handle !removekey command to remove SSH keys from the lab environment."""
        if message.channel.name != "prolug_lab_environment":
            return

        username = message.author.name
        safe_username = _sanitize_username(username)
        if not safe_username:
            logger.warning("Rejected unsafe username for SSH removekey: %s", username)
            await message.channel.send("Your username contains characters that aren't supported. Please contact an administrator for manual key removal.")
            return

        try:
            # Check if user has a key
            returncode, stdout, stderr = await _run_ssh_command(
                f"sudo grep -iF {shlex.quote('# Owner: ' + safe_username)} {AUTHORIZED_KEYS_PATH}"
            )

            if returncode != 0:
                await message.channel.send(f"{username}, you don't have a key in the authorized_keys file.")
                return

            # Remove the key using sed with case-insensitive matching
            returncode, stdout, stderr = await _run_ssh_command(
                f"sudo sed -i {shlex.quote('/# Owner: ' + safe_username + '/I{N;d;}')} {AUTHORIZED_KEYS_PATH}"
            )

            if returncode == 0:
                await message.channel.send(f"SSH key removed successfully for {username}!")
            else:
                logger.error("SSH removekey failed for %s: returncode=%s stderr=%s",
                             username, returncode, stderr)
                await message.channel.send("Error removing SSH key. Please try again later.")
        except asyncio.TimeoutError:
            logger.error("SSH removekey timed out for %s", username)
            await message.channel.send("SSH connection timed out. Please try again later.")
        except Exception:
            logger.error("Unexpected error in SSH removekey for %s", username, exc_info=True)
            await message.channel.send("An unexpected error occurred. Please try again later.")

    async def handle_keystatus_command(self, message: discord.Message) -> None:
        """Handle !keystatus command to check if user has an SSH key."""
        if message.channel.name != "prolug_lab_environment":
            return

        username = message.author.name
        safe_username = _sanitize_username(username)
        if not safe_username:
            logger.warning("Rejected unsafe username for SSH keystatus: %s", username)
            await message.channel.send("Your username contains characters that aren't supported. Please contact an administrator.")
            return

        try:
            # Use grep -A 1 to get the owner comment line AND the next line (the key)
            returncode, stdout, stderr = await _run_ssh_command(
                f"sudo grep -iFA 1 {shlex.quote('# Owner: ' + safe_username)} {AUTHORIZED_KEYS_PATH}"
            )

            if returncode != 0:
                await message.channel.send(f"{username}, you don't have a key in the authorized_keys file.")
                return

            # Parse the output - first line is comment, second line is the key
            lines = stdout.strip().split('\n')
            if len(lines) >= 2:
                ssh_key = lines[1]
                await message.channel.send(f"{username}, your SSH key is:\n```\n{ssh_key}\n```")
            else:
                await message.channel.send(f"{username}, found your key entry but couldn't retrieve the key.")
        except asyncio.TimeoutError:
            logger.error("SSH keystatus timed out for %s", username)
            await message.channel.send("SSH connection timed out. Please try again later.")
        except Exception:
            logger.error("Unexpected error in SSH keystatus for %s", username, exc_info=True)
            await message.channel.send("An unexpected error occurred. Please try again later.")


def is_authorized_user():
    """Decorator to check if user is authorized."""
    async def predicate(ctx):
        return ctx.author.name.lower() in [user.lower() for user in AUTHORIZED_USERS]
    return commands.check(predicate)
