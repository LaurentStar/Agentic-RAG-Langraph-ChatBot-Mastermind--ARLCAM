"""
Player Commands Cog.

Discord slash commands for player-facing game interactions.
Uses per-user OAuth authentication - each user must link their Discord account.

Naming Convention:
- Category uses underscores: game_session
- Command name uses hyphens: join, leave, status
- Full format: <category>-<command>

Copyright © 2024
"""

import os
import logging
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from app.decorators import requires_linked_account

logger = logging.getLogger("discord_bot")


class PlayerCommands(commands.Cog, name="player_commands"):
    """
    Player commands for game interactions.
    
    All commands require a linked Discord account.
    
    Commands:
    - /game_session-join: Join a game session
    - /game_session-start: Start a game session (requires START_GAME privilege)
    """
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
        # Configuration from environment
        self.game_server_url = os.getenv("GAME_SERVER_URL", "http://localhost:5000")
        
        # HTTP session for async requests
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        logger.info("PlayerCommands cog initialized")
        logger.info(f"  Game Server URL: {self.game_server_url}")
    
    async def cog_load(self) -> None:
        """Called when the cog is loaded."""
        self._http_session = aiohttp.ClientSession()
        logger.info("PlayerCommands cog loaded, HTTP session created")
    
    async def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        if self._http_session:
            await self._http_session.close()
            logger.info("PlayerCommands HTTP session closed")
    
    def _get_user_headers(self, interaction: discord.Interaction) -> dict:
        """
        Get authorization headers using the user's JWT token.
        
        The token is injected by @requires_linked_account decorator.
        
        Args:
            interaction: Discord interaction with jwt_token in extras
            
        Returns:
            Headers dict with Bearer token
        """
        jwt_token = interaction.extras.get('jwt_token', '')
        return {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
    
    def _get_session_from_channel(self, channel_id: int) -> Optional[str]:
        """
        Get session ID from GameChat cog's channel registry.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Session ID if channel is registered, None otherwise
        """
        game_chat_cog = self.bot.get_cog("game_chat")
        if game_chat_cog:
            return game_chat_cog.get_session_for_channel(channel_id)
        return None
    
    async def _handle_error_response(
        self,
        interaction: discord.Interaction,
        response: aiohttp.ClientResponse,
        action: str
    ) -> None:
        """
        Handle error responses from game server.
        
        Args:
            interaction: Discord interaction
            response: aiohttp response object
            action: Description of action (for error messages)
        """
        if response.status == 403:
            await interaction.followup.send(
                "❌ **Permission Denied**\n\n"
                "You don't have the required privileges for this action.\n"
                "Contact a game admin if you believe this is an error.",
                ephemeral=True
            )
        elif response.status == 401:
            await interaction.followup.send(
                "❌ **Authentication Failed**\n\n"
                "Your session may have expired. Try running the command again.",
                ephemeral=True
            )
        elif response.status == 404:
            await interaction.followup.send(
                f"❌ **Not Found**\n\nThe session was not found or is not available.",
                ephemeral=True
            )
        elif response.status == 400:
            try:
                data = await response.json()
                error_msg = data.get('message', data.get('error', 'Bad request'))
            except Exception:
                error_msg = await response.text()
            await interaction.followup.send(
                f"❌ **Cannot {action.title()}**\n\n{error_msg}",
                ephemeral=True
            )
        else:
            text = await response.text()
            await interaction.followup.send(
                f"❌ Failed to {action}: HTTP {response.status}\n```{text}```",
                ephemeral=True
            )
    
    # =============================================
    # Game Session Commands
    # =============================================
    
    @app_commands.command(
        name="game_session-join",
        description="Join a game session"
    )
    @app_commands.describe(
        session_id="Session ID (optional if in a registered channel)"
    )
    @requires_linked_account
    async def join_session(
        self,
        interaction: discord.Interaction,
        session_id: Optional[str] = None
    ) -> None:
        """
        Join a game session.
        
        Requires linked account.
        
        If executed in a channel registered to a session, that session
        is used by default. Otherwise, session_id must be provided.
        
        Args:
            interaction: Discord interaction
            session_id: Optional session ID (auto-detected from channel if not provided)
        """
        await interaction.response.defer(ephemeral=True)
        
        if not self._http_session:
            await interaction.followup.send("❌ HTTP session not initialized", ephemeral=True)
            return
        
        player_name = interaction.extras.get('player_name', 'Unknown')
        
        # Determine session ID
        effective_session_id = session_id
        auto_detected = False
        
        if not effective_session_id:
            # Try to get session from channel
            effective_session_id = self._get_session_from_channel(interaction.channel_id)
            if effective_session_id:
                auto_detected = True
        
        # If still no session ID, show error
        if not effective_session_id:
            embed = discord.Embed(
                title="❌ No Session Specified",
                description=(
                    "This channel is not linked to a game session.\n\n"
                    "**Options:**\n"
                    "• Provide a session ID: `/game_session-join session_id:YOUR_ID`\n"
                    "• Use `/game_session-list` to find available sessions\n"
                    "• Run this command in a channel linked to a session"
                ),
                color=0xFF6B6B
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Call game server to join session
        url = f"{self.game_server_url}/game/sessions/{effective_session_id}/join"
        payload = {"player_display_name": player_name}
        
        try:
            async with self._http_session.post(
                url, 
                json=payload, 
                headers=self._get_user_headers(interaction)
            ) as response:
                if response.status == 200:
                    embed = discord.Embed(
                        title="✅ Joined Game Session",
                        description=f"Welcome, **{player_name}**!",
                        color=0x00FF00
                    )
                    
                    # Show session ID (truncated if long)
                    session_display = f"`{effective_session_id[:8]}...`" if len(effective_session_id) > 8 else f"`{effective_session_id}`"
                    embed.add_field(name="Session ID", value=session_display, inline=True)
                    
                    if auto_detected:
                        embed.add_field(
                            name="Channel", 
                            value=f"<#{interaction.channel_id}>", 
                            inline=True
                        )
                    
                    embed.add_field(
                        name="Next Steps",
                        value="Use `/game_session-list` to see session details.",
                        inline=False
                    )
                    
                    embed.set_footer(text="Good luck! May the best bluffer win.")
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    
                    source = "(auto-detected from channel)" if auto_detected else "(explicit)"
                    logger.info(f"{player_name} joined session {effective_session_id} {source}")
                else:
                    await self._handle_error_response(interaction, response, "join session")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to game server: {e}")
            await interaction.followup.send(f"❌ Failed to connect to game server: {e}", ephemeral=True)
        except Exception as e:
            logger.error(f"Unexpected error joining session: {e}")
            await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)
    
    @app_commands.command(
        name="game_session-start",
        description="Start a game session (requires START_GAME privilege)"
    )
    @app_commands.describe(
        session_id="Session ID (optional if in a registered channel)"
    )
    @requires_linked_account
    async def start_session(
        self,
        interaction: discord.Interaction,
        session_id: Optional[str] = None
    ) -> None:
        """
        Start a game session.
        
        Requires linked account with START_GAME privilege.
        
        If executed in a channel registered to a session, that session
        is used by default. Otherwise, session_id must be provided.
        
        Args:
            interaction: Discord interaction
            session_id: Optional session ID (auto-detected from channel if not provided)
        """
        await interaction.response.defer(ephemeral=True)
        
        if not self._http_session:
            await interaction.followup.send("❌ HTTP session not initialized", ephemeral=True)
            return
        
        player_name = interaction.extras.get('player_name', 'Unknown')
        
        # Determine session ID
        effective_session_id = session_id
        auto_detected = False
        
        if not effective_session_id:
            # Try to get session from channel
            effective_session_id = self._get_session_from_channel(interaction.channel_id)
            if effective_session_id:
                auto_detected = True
        
        # If still no session ID, show error
        if not effective_session_id:
            embed = discord.Embed(
                title="❌ No Session Specified",
                description=(
                    "This channel is not linked to a game session.\n\n"
                    "**Options:**\n"
                    "• Provide a session ID: `/game_session-start session_id:YOUR_ID`\n"
                    "• Use `/game_session-list` to find available sessions\n"
                    "• Run this command in a channel linked to a session"
                ),
                color=0xFF6B6B
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Call game server to start session
        url = f"{self.game_server_url}/admin/sessions/{effective_session_id}/start"
        
        try:
            async with self._http_session.post(
                url, 
                headers=self._get_user_headers(interaction)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    embed = discord.Embed(
                        title="🎮 Game Started!",
                        description=f"Started by **{player_name}**",
                        color=0x00FF00
                    )
                    
                    # Session name
                    session_name = data.get('session_name', 'Unknown')
                    embed.add_field(name="Session", value=session_name, inline=True)
                    
                    # Player count
                    player_count = data.get('player_count', '?')
                    max_players = data.get('max_players', '?')
                    embed.add_field(name="Players", value=f"{player_count}/{max_players}", inline=True)
                    
                    # Turn info
                    turn_number = data.get('turn_number', 1)
                    current_phase = data.get('current_phase', 'phase1')
                    phase_display = {
                        'phase1': 'Phase 1 (Actions)',
                        'lockout1': 'Lockout 1',
                        'phase2': 'Phase 2 (Reactions)',
                        'lockout2': 'Lockout 2',
                        'broadcast': 'Broadcast'
                    }.get(current_phase, current_phase)
                    
                    embed.add_field(
                        name="Turn", 
                        value=f"Turn {turn_number} - {phase_display}", 
                        inline=False
                    )
                    
                    if auto_detected:
                        embed.add_field(
                            name="Channel", 
                            value=f"<#{interaction.channel_id}>", 
                            inline=True
                        )
                    
                    embed.set_footer(text="Let the games begin! May the best bluffer win.")
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    
                    source = "(auto-detected from channel)" if auto_detected else "(explicit)"
                    logger.info(f"{player_name} started session {effective_session_id} {source}")
                else:
                    await self._handle_error_response(interaction, response, "start session")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to game server: {e}")
            await interaction.followup.send(f"❌ Failed to connect to game server: {e}", ephemeral=True)
        except Exception as e:
            logger.error(f"Unexpected error starting session: {e}")
            await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Load the PlayerCommands cog."""
    await bot.add_cog(PlayerCommands(bot))

