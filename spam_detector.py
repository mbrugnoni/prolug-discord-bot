import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import timedelta

import discord

from config import (
    AUTHORIZED_USERS,
    SPAM_CHANNEL_THRESHOLD,
    SPAM_NOTIFY_CHANNEL,
    SPAM_TIME_WINDOW_SECONDS,
    SPAM_TIMEOUT_MINUTES,
)

logger = logging.getLogger(__name__)


@dataclass
class TrackedMessage:
    channel_id: int
    timestamp: float
    message: discord.Message


class SpamDetector:
    """Detects cross-channel spam by tracking how many distinct channels
    a user posts in within a sliding time window."""

    def __init__(self, client: discord.Client):
        self._client = client
        self._channel_threshold = SPAM_CHANNEL_THRESHOLD
        self._time_window = SPAM_TIME_WINDOW_SECONDS
        self._timeout_minutes = SPAM_TIMEOUT_MINUTES
        self._user_messages: dict[int, list[TrackedMessage]] = {}
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = 60.0

    async def check_message(self, message: discord.Message) -> bool:
        """Track the message and check for cross-channel spam.

        Returns True if the message is spam (caller should stop processing).
        Returns False if the message is clean.
        """
        if self._should_skip(message):
            return False

        user_id = message.author.id
        now = time.monotonic()

        self._maybe_cleanup(now)
        self._prune_user(user_id, now)

        if user_id not in self._user_messages:
            self._user_messages[user_id] = []

        self._user_messages[user_id].append(
            TrackedMessage(
                channel_id=message.channel.id,
                timestamp=now,
                message=message,
            )
        )

        distinct_channels = len({tm.channel_id for tm in self._user_messages[user_id]})

        if distinct_channels >= self._channel_threshold:
            await self._take_action(user_id, self._user_messages[user_id])
            self._user_messages.pop(user_id, None)
            return True

        return False

    def _should_skip(self, message: discord.Message) -> bool:
        """Return True if this message should be excluded from spam checking."""
        if message.author.bot:
            return True
        if message.guild is None:
            return True
        if message.author.guild_permissions.administrator:
            return True
        if message.author.name.lower() in [u.lower() for u in AUTHORIZED_USERS]:
            return True
        return False

    def _prune_user(self, user_id: int, now: float) -> None:
        """Remove entries older than the time window for a specific user."""
        entries = self._user_messages.get(user_id)
        if not entries:
            return
        cutoff = now - self._time_window
        pruned = [tm for tm in entries if tm.timestamp >= cutoff]
        if pruned:
            self._user_messages[user_id] = pruned
        else:
            del self._user_messages[user_id]

    def _maybe_cleanup(self, now: float) -> None:
        """Periodically remove users with no recent activity."""
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        cutoff = now - self._time_window
        stale_users = [
            uid for uid, entries in self._user_messages.items()
            if not entries or entries[-1].timestamp < cutoff
        ]
        for uid in stale_users:
            del self._user_messages[uid]

    async def _take_action(self, user_id: int, messages: list[TrackedMessage]) -> None:
        """Delete all tracked messages, timeout the user, and notify moderators."""
        member = messages[0].message.author
        channel_count = len({tm.channel_id for tm in messages})

        # Delete all tracked messages concurrently
        results = await asyncio.gather(
            *(self._safe_delete(tm.message) for tm in messages),
            return_exceptions=True,
        )
        deleted_count = sum(1 for r in results if r is True)

        logger.warning(
            "Spam detected: user=%s (id=%d) posted to %d channels in %ds. "
            "Deleted %d/%d messages.",
            member.name, user_id, channel_count,
            self._time_window, deleted_count, len(messages),
        )

        # Timeout the user
        try:
            await member.timeout(
                timedelta(minutes=self._timeout_minutes),
                reason="Cross-channel spam detected",
            )
            logger.info(
                "Timed out user %s (id=%d) for %d minutes",
                member.name, user_id, self._timeout_minutes,
            )
        except discord.Forbidden:
            logger.error(
                "Cannot timeout user %s (id=%d): missing permission or user has higher role",
                member.name, user_id,
            )
        except discord.HTTPException as e:
            logger.error("Failed to timeout user %s (id=%d): %s", member.name, user_id, e)

        # Notify moderator channel
        await self._notify_moderators(member, channel_count, len(messages), deleted_count)

    async def _safe_delete(self, message: discord.Message) -> bool:
        """Attempt to delete a message. Returns True on success."""
        try:
            await message.delete()
            return True
        except discord.NotFound:
            return True
        except discord.Forbidden:
            logger.warning(
                "Cannot delete message in #%s: missing MANAGE_MESSAGES permission",
                message.channel.name,
            )
            return False
        except discord.HTTPException as e:
            logger.warning("Failed to delete message in #%s: %s", message.channel.name, e)
            return False

    async def _notify_moderators(
        self, member: discord.Member, channel_count: int,
        total_messages: int, deleted_count: int,
    ) -> None:
        """Send a notification to the moderator channel."""
        for guild in self._client.guilds:
            for channel in guild.text_channels:
                if channel.name == SPAM_NOTIFY_CHANNEL:
                    try:
                        await channel.send(
                            f"**Spam Detected**\n"
                            f"User: {member.mention} ({member.name})\n"
                            f"Channels: {channel_count} channels in {self._time_window}s\n"
                            f"Messages deleted: {deleted_count}/{total_messages}\n"
                            f"Action: Timed out for {self._timeout_minutes} minutes"
                        )
                    except discord.HTTPException as e:
                        logger.error("Failed to send spam notification: %s", e)
                    return
        logger.warning("Could not find '%s' channel to send spam notification", SPAM_NOTIFY_CHANNEL)
