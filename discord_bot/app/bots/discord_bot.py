"""
Discord Bot Class.

The main Discord bot for the Coup game.
Handles Discord interactions, cog loading, and command sync.
"""

import os
import logging
import platform

import discord
from discord.ext import commands


logger = logging.getLogger("discord_bot")

# Discord intents configuration
intents = discord.Intents.default()
intents.message_content = True  # Required for game chat


class DiscordBot(commands.Bot):
    """
    Coup Game Discord Bot.
    
    Handles Discord interactions and game chat integration.
    """
    
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or(os.getenv("PREFIX", "!")),
            intents=intents,
            help_command=None,
        )
        self.logger = logger
        self.bot_prefix = os.getenv("PREFIX", "!")

    async def load_cogs(self) -> None:
        """Load cogs from the app/cogs directory."""
        cogs_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "cogs"
        )
        
        for file in os.listdir(cogs_path):
            if file.endswith(".py") and not file.startswith("_"):
                extension = file[:-3]
                try:
                    await self.load_extension(f"app.cogs.{extension}")
                    self.logger.info(f"Loaded cog: {extension}")
                except Exception as e:
                    self.logger.error(f"Failed to load cog {extension}: {e}")

    async def setup_hook(self) -> None:
        """Called when the bot starts."""
        self.logger.info(f"Logged in as {self.user.name}")
        self.logger.info(f"discord.py version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(f"Platform: {platform.system()} {platform.release()}")
        self.logger.info("-------------------")
        
        await self.load_cogs()
        
        # Auto-sync slash commands with test guild
        await self.auto_sync_commands()
    
    async def auto_sync_commands(self) -> None:
        """
        Auto-sync slash commands with Discord.
        
        Uses TEST_GUILD_ID for instant updates (guild commands update immediately,
        global commands take up to 1 hour).
        """
        from app.services.command_sync_service import CommandSyncService
        
        test_guild_id = os.getenv("TEST_GUILD_ID")
        
        if not test_guild_id:
            self.logger.warning(
                "TEST_GUILD_ID not set. Skipping auto-sync. "
                "Set this env var for instant slash command updates."
            )
            return
        
        try:
            result = await CommandSyncService.auto_sync(self, test_guild_id)
            
            if result.get("status") == "success":
                new_count = len(result.get("new_registered", []))
                pending_count = len(result.get("pending_changes", []))
                orphaned_count = len(result.get("orphaned", []))
                
                if new_count > 0:
                    self.logger.info(f"Auto-registered {new_count} new commands")
                if pending_count > 0:
                    self.logger.warning(
                        f"{pending_count} commands have changes pending sync. "
                        f"Use /admin/commands/sync-status API to review."
                    )
                if orphaned_count > 0:
                    self.logger.warning(
                        f"{orphaned_count} orphaned commands on Discord. "
                        f"Use /admin/commands/sync API to clean up."
                    )
            elif result.get("status") == "error":
                self.logger.error(f"Auto-sync failed: {result.get('error')}")
                
        except Exception as e:
            self.logger.error(f"Auto-sync error: {e}")

    async def on_message(self, message: discord.Message) -> None:
        """Process incoming messages."""
        # Ignore bot messages
        if message.author == self.user or message.author.bot:
            return
        
        await self.process_commands(message)

    async def on_command_error(self, context, error) -> None:
        """Handle command errors."""
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                description=f"Please wait {error.retry_after:.1f}s before using this command again.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description=f"Missing permissions: {', '.join(error.missing_permissions)}",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                description=str(error).capitalize(),
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        else:
            self.logger.error(f"Command error: {error}")
            raise error

