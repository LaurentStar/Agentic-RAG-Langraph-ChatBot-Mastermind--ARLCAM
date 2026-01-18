"""
Game Chat Cog.

Handles cross-platform game chat integration with the game server.
Supports multiple channels, each linked to different game sessions.
Messages from registered game channels are forwarded to the game server
for broadcast to all platforms.

Copyright © 2024
"""

import os
import logging
from typing import Dict, Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from app.services.logging_service import LoggingService

logger = logging.getLogger("discord_bot")


class GameChat(commands.Cog, name="game_chat"):
    """
    Handles cross-platform game chat integration.
    
    Features:
    - Multi-channel support: each channel can be linked to a different session
    - Forwards messages from registered channels to game_server
    - Receives broadcasts from game_server and routes to correct channel
    - Runtime channel registration without restart
    - Startup sync from game_server
    """
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
        # Configuration from environment
        self.game_server_url = os.getenv("GAME_SERVER_URL", "http://localhost:4000")
        
        # Channel registries (in-memory, synced from game_server)
        # channel_id (int) -> session_id (str)
        self.channel_sessions: Dict[int, str] = {}
        # session_id (str) -> channel_id (int) for reverse lookup (broadcasts)
        self.session_channels: Dict[str, int] = {}
        
        # HTTP session for async requests
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        logger.info("GameChat cog initialized (multi-channel mode)")
        logger.info(f"  Game Server URL: {self.game_server_url}")
    
    async def cog_load(self) -> None:
        """Called when the cog is loaded."""
        self._http_session = aiohttp.ClientSession()
        logger.info("GameChat cog loaded, HTTP session created")
        
        # Sync channel registrations from game_server on startup
        await self._sync_from_game_server()
    
    async def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        if self._http_session:
            await self._http_session.close()
            logger.info("GameChat HTTP session closed")
    
    # =============================================
    # Channel Registry Management
    # =============================================
    
    def register_channel(self, channel_id: int, session_id: str) -> None:
        """
        Register a channel to a game session.
        
        Args:
            channel_id: Discord channel ID
            session_id: Game session ID
        """
        # If channel was registered to a different session, clean up
        old_session = self.channel_sessions.get(channel_id)
        if old_session and old_session != session_id:
            self.session_channels.pop(old_session, None)
        
        self.channel_sessions[channel_id] = session_id
        self.session_channels[session_id] = channel_id
        logger.info(f"Registered channel {channel_id} -> session {session_id}")
    
    def unregister_channel(self, channel_id: int) -> Optional[str]:
        """
        Unregister a channel from its game session.
        
        Args:
            channel_id: Discord channel ID
        
        Returns:
            Session ID that was unregistered, or None if channel wasn't registered
        """
        session_id = self.channel_sessions.pop(channel_id, None)
        if session_id:
            self.session_channels.pop(session_id, None)
            logger.info(f"Unregistered channel {channel_id} (was session {session_id})")
        return session_id
    
    def get_session_for_channel(self, channel_id: int) -> Optional[str]:
        """Get session ID for a channel."""
        return self.channel_sessions.get(channel_id)
    
    def get_channel_for_session(self, session_id: str) -> Optional[int]:
        """Get channel ID for a session (for routing broadcasts)."""
        return self.session_channels.get(session_id)
    
    async def _sync_from_game_server(self) -> int:
        """
        Fetch active sessions from game_server and populate channel registry.
        
        Called on startup and via /syncchannels command.
        
        Returns:
            Number of channels synced
        """
        if not self._http_session:
            logger.warning("HTTP session not initialized, cannot sync")
            return 0
        
        url = f"{self.game_server_url}/game/sessions/discord-channels"
        
        try:
            async with self._http_session.get(url) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.warning(f"Failed to sync from game server: HTTP {response.status} - {text}")
                    return 0
                
                data = await response.json()
                channels = data.get('channels', [])
                
                # Clear existing registrations and repopulate
                self.channel_sessions.clear()
                self.session_channels.clear()
                
                count = 0
                for item in channels:
                    discord_channel_id = item.get('discord_channel_id')
                    session_id = item.get('session_id')
                    
                    if discord_channel_id and session_id:
                        try:
                            channel_id = int(discord_channel_id)
                            self.register_channel(channel_id, session_id)
                            count += 1
                        except ValueError:
                            logger.warning(f"Invalid channel ID: {discord_channel_id}")
                
                logger.info(f"Synced {count} channel registrations from game server")
                return count
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to game server for sync: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error during sync: {e}")
            return 0
    
    # =============================================
    # Message Handling
    # =============================================
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Listen for messages in registered game channels and forward to game_server.
        
        Args:
            message: The Discord message
        """
        # Look up session for this channel
        session_id = self.channel_sessions.get(message.channel.id)
        if not session_id:
            return  # Not a registered game channel
        
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Ignore empty messages
        if not message.content.strip():
            return
        
        # Log the message flow
        content_preview = message.content[:50] + "..." if len(message.content) > 50 else message.content
        logger.info(
            f"[CHAT-FLOW] Discord → GameServer: session={session_id} "
            f"sender={message.author.display_name} content=\"{content_preview}\""
        )
        
        # Forward to game server
        success = await self._send_to_game_server(
            session_id=session_id,
            sender=message.author.display_name,
            content=message.content,
            message=message  # Pass message for DB logging
        )
        
        # Log to database
        if message.guild:
            LoggingService.log_message(
                guild_id=str(message.guild.id),
                channel_id=str(message.channel.id),
                user_id=str(message.author.id),
                user_name=message.author.display_name,
                content=message.content,
                session_id=session_id,
                direction="outgoing"
            )
    
    async def _send_to_game_server(
        self, 
        session_id: str, 
        sender: str, 
        content: str,
        message: Optional[discord.Message] = None
    ) -> bool:
        """
        POST message to game_server chat queue.
        
        Args:
            session_id: Target game session
            sender: Sender's display name
            content: Message content
            message: Original Discord message (for error logging)
        
        Returns:
            True if successful, False otherwise
        """
        if not self._http_session:
            logger.warning("[CHAT-FLOW] HTTP session not initialized")
            return False
        
        url = f"{self.game_server_url}/game/chat/{session_id}/send"
        headers = {
            "Coup-Service-Key": os.getenv("SERVICE_API_KEY", ""),
            "Content-Type": "application/json"
        }
        payload = {
            "sender": sender,
            "platform": "discord",
            "content": content
        }
        
        logger.debug(f"[CHAT-FLOW] POST {url} payload={payload}")
        
        try:
            async with self._http_session.post(url, json=payload, headers=headers) as response:
                if response.status == 201:
                    logger.info(
                        f"[CHAT-FLOW] GameServer accepted: session={session_id} "
                        f"sender={sender} status=201"
                    )
                    return True
                else:
                    text = await response.text()
                    logger.warning(
                        f"[CHAT-FLOW] GameServer rejected: session={session_id} "
                        f"sender={sender} status={response.status} response={text[:100]}"
                    )
                    # Log error to database
                    if message and message.guild:
                        LoggingService.log_error(
                            error_type="GameServerError",
                            error_message=f"HTTP {response.status}: {text[:200]}",
                            guild_id=str(message.guild.id),
                            channel_id=str(message.channel.id),
                            context={"session_id": session_id, "sender": sender}
                        )
                    return False
                    
        except aiohttp.ClientError as e:
            logger.error(f"[CHAT-FLOW] Connection failed: session={session_id} error={e}")
            if message and message.guild:
                LoggingService.log_error(
                    error_type="ConnectionError",
                    error_message=str(e),
                    guild_id=str(message.guild.id),
                    channel_id=str(message.channel.id),
                    context={"session_id": session_id, "sender": sender}
                )
            return False
        except Exception as e:
            logger.error(f"[CHAT-FLOW] Unexpected error: session={session_id} error={e}")
            if message and message.guild:
                LoggingService.log_error(
                    error_type="UnexpectedError",
                    error_message=str(e),
                    guild_id=str(message.guild.id),
                    channel_id=str(message.channel.id),
                    context={"session_id": session_id, "sender": sender}
                )
            return False
    
    # =============================================
    # Broadcast Handling (called by broadcast_server.py)
    # =============================================
    
    async def post_broadcast(self, session_id: str, messages: list) -> bool:
        """
        Post broadcast messages to the appropriate game channel.
        
        Called by the broadcast server when game_server pushes a chat update.
        Routes to the correct channel based on session_id.
        
        Args:
            session_id: Game session the messages belong to
            messages: List of message dicts with sender, platform, content
        
        Returns:
            True if successful, False otherwise
        """
        # Look up channel for this session
        channel_id = self.session_channels.get(session_id)
        if not channel_id:
            logger.warning(f"No channel registered for session {session_id}")
            return False
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            logger.error(f"Could not find channel {channel_id} for session {session_id}")
            return False
        
        # Build embed
        embed = discord.Embed(
            title="📢 Game Chat Update",
            color=0x5865F2  # Discord blurple
        )
        
        for msg in messages:
            # Platform indicator
            platform = msg.get('platform', 'unknown')
            if platform == 'discord':
                icon = "🎮"
            elif platform == 'slack':
                icon = "💬"
            elif platform == 'twitter':
                icon = "🐦"
            elif platform == 'bluesky':
                icon = "🦋"
            else:
                icon = "📝"
            
            embed.add_field(
                name=f"{icon} {msg.get('sender', 'Unknown')}",
                value=msg.get('content', '(empty)')[:1024],  # Field value limit
                inline=False
            )
        
        try:
            await channel.send(embed=embed)
            logger.info(f"Posted broadcast ({len(messages)} msgs) to channel {channel_id} for session {session_id}")
            return True
        except discord.DiscordException as e:
            logger.error(f"Failed to post broadcast: {e}")
            return False
    
    # =============================================
    # Slash Commands
    # =============================================
    
    @app_commands.command(
        name="registerchannel",
        description="Link this channel to a game session"
    )
    @app_commands.describe(session_id="The game session ID to link to this channel")
    @app_commands.default_permissions(administrator=True)
    async def register_channel_cmd(self, interaction: discord.Interaction, session_id: str) -> None:
        """
        Register current channel to a game session.
        
        Args:
            interaction: Discord interaction
            session_id: Game session ID
        """
        channel_id = interaction.channel_id
        
        # Register locally
        self.register_channel(channel_id, session_id)
        
        await interaction.response.send_message(
            f"✅ Channel <#{channel_id}> linked to session `{session_id}`\n"
            f"Messages in this channel will now be forwarded to the game.",
            ephemeral=True
        )
        logger.info(f"Channel {channel_id} registered to session {session_id} by {interaction.user}")
    
    @app_commands.command(
        name="unregisterchannel",
        description="Unlink this channel from its game session"
    )
    @app_commands.default_permissions(administrator=True)
    async def unregister_channel_cmd(self, interaction: discord.Interaction) -> None:
        """
        Unregister current channel from its game session.
        
        Args:
            interaction: Discord interaction
        """
        channel_id = interaction.channel_id
        session_id = self.unregister_channel(channel_id)
        
        if session_id:
            await interaction.response.send_message(
                f"✅ Channel unlinked from session `{session_id}`",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "⚠️ This channel is not linked to any game session",
                ephemeral=True
            )
    
    @app_commands.command(
        name="listchannels",
        description="Show all registered game channels"
    )
    @app_commands.default_permissions(administrator=True)
    async def list_channels_cmd(self, interaction: discord.Interaction) -> None:
        """
        List all registered channel→session mappings.
        
        Args:
            interaction: Discord interaction
        """
        if not self.channel_sessions:
            await interaction.response.send_message(
                "📋 No channels are currently registered.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📋 Registered Game Channels",
            color=0x5865F2
        )
        
        for channel_id, session_id in self.channel_sessions.items():
            channel = self.bot.get_channel(channel_id)
            channel_name = channel.name if channel else f"(unknown: {channel_id})"
            embed.add_field(
                name=f"#{channel_name}",
                value=f"Session: `{session_id}`",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="syncchannels",
        description="Re-sync channel registrations from game server"
    )
    @app_commands.default_permissions(administrator=True)
    async def sync_channels_cmd(self, interaction: discord.Interaction) -> None:
        """
        Re-sync channel registrations from game_server.
        
        Args:
            interaction: Discord interaction
        """
        await interaction.response.defer(ephemeral=True)
        
        count = await self._sync_from_game_server()
        
        await interaction.followup.send(
            f"✅ Synced {count} channel registration(s) from game server",
            ephemeral=True
        )
    
    @app_commands.command(
        name="gamechatstatus",
        description="Check game chat configuration status"
    )
    async def status_cmd(self, interaction: discord.Interaction) -> None:
        """
        Display current game chat configuration.
        
        Args:
            interaction: Discord interaction
        """
        embed = discord.Embed(
            title="🎮 Game Chat Status",
            color=0x5865F2
        )
        
        embed.add_field(
            name="Game Server",
            value=self.game_server_url,
            inline=False
        )
        embed.add_field(
            name="Registered Channels",
            value=str(len(self.channel_sessions)),
            inline=True
        )
        embed.add_field(
            name="HTTP Session",
            value="✅ Active" if self._http_session else "❌ Not initialized",
            inline=True
        )
        
        # Show this channel's status
        current_session = self.channel_sessions.get(interaction.channel_id)
        embed.add_field(
            name="This Channel",
            value=f"Linked to `{current_session}`" if current_session else "Not linked",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load the GameChat cog."""
    await bot.add_cog(GameChat(bot))
