"""
Admin Commands Cog.

Discord slash commands for game session management.
Uses per-user OAuth authentication - each user must link their Discord account.

Naming Convention:
- Category uses underscores: game_session
- Command name uses hyphens: create, list, end
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


class AdminCommands(commands.Cog, name="admin_commands"):
    """
    Admin commands for game session management.
    
    All commands require a linked Discord account.
    The game server validates user privileges for admin actions.
    
    Commands:
    - /game_session-create: Create a new game session
    - /game_session-list: List all game sessions
    - /game_session-end: End a game session
    - /game_session-register-channel: Link channel to session
    """
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
        # Configuration from environment
        self.game_server_url = os.getenv("GAME_SERVER_URL", "http://localhost:5000")
        
        # HTTP session for async requests
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        logger.info("AdminCommands cog initialized")
        logger.info(f"  Game Server URL: {self.game_server_url}")
    
    async def cog_load(self) -> None:
        """Called when the cog is loaded."""
        self._http_session = aiohttp.ClientSession()
        logger.info("AdminCommands cog loaded, HTTP session created")
    
    async def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        if self._http_session:
            await self._http_session.close()
            logger.info("AdminCommands HTTP session closed")
    
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
                f"❌ **Not Found**\n\nThe requested resource was not found.",
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
        name="game_session-create",
        description="Create a new game session"
    )
    @app_commands.describe(
        name="Session name",
        max_players="Maximum players (2-6)",
        turn_limit="Maximum turns (0 = unlimited)",
        upgrades_enabled="Allow action upgrades",
        phase1_duration="Phase 1 (actions) duration in minutes",
        phase2_duration="Phase 2 (reactions) duration in minutes"
    )
    @requires_linked_account
    async def create_session(
        self,
        interaction: discord.Interaction,
        name: str,
        max_players: int = 6,
        turn_limit: int = 10,
        upgrades_enabled: bool = True,
        phase1_duration: int = 50,
        phase2_duration: int = 20
    ) -> None:
        """
        Create a new game session.
        
        Requires linked account with admin privileges.
        
        Args:
            interaction: Discord interaction
            name: Session name
            max_players: Max players (2-6)
            turn_limit: Max turns (0 = unlimited)
            upgrades_enabled: Allow upgrades
            phase1_duration: Phase 1 duration in minutes
            phase2_duration: Phase 2 duration in minutes
        """
        await interaction.response.defer(ephemeral=True)
        
        if not self._http_session:
            await interaction.followup.send("❌ HTTP session not initialized", ephemeral=True)
            return
        
        # Validate parameters
        if max_players < 2 or max_players > 6:
            await interaction.followup.send("❌ max_players must be between 2 and 6", ephemeral=True)
            return
        
        player_name = interaction.extras.get('player_name', 'Unknown')
        url = f"{self.game_server_url}/admin/sessions"
        payload = {
            "session_name": name,
            "max_players": max_players,
            "turn_limit": turn_limit,
            "upgrades_enabled": upgrades_enabled,
            "phase1_duration": phase1_duration,
            "lockout1_duration": 10,
            "phase2_duration": phase2_duration,
            "lockout2_duration": 10,
            "broadcast_duration": 1
        }
        
        try:
            async with self._http_session.post(
                url, 
                json=payload, 
                headers=self._get_user_headers(interaction)
            ) as response:
                if response.status == 201:
                    data = await response.json()
                    session_id = data.get('session_id', 'Unknown')
                    
                    embed = discord.Embed(
                        title="✅ Game Session Created",
                        description=f"Created by **{player_name}**",
                        color=0x00FF00
                    )
                    embed.add_field(name="Session ID", value=f"`{session_id}`", inline=False)
                    embed.add_field(name="Name", value=name, inline=True)
                    embed.add_field(name="Max Players", value=str(max_players), inline=True)
                    embed.add_field(name="Turn Limit", value=str(turn_limit) if turn_limit > 0 else "Unlimited", inline=True)
                    embed.add_field(name="Upgrades", value="✅ Enabled" if upgrades_enabled else "❌ Disabled", inline=True)
                    embed.set_footer(text=f"Use /game_session-register-channel to link a channel")
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    logger.info(f"Session {session_id} created by {interaction.user} ({player_name})")
                else:
                    await self._handle_error_response(interaction, response, "create session")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to game server: {e}")
            await interaction.followup.send(f"❌ Failed to connect to game server: {e}", ephemeral=True)
        except Exception as e:
            logger.error(f"Unexpected error creating session: {e}")
            await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)
    
    @app_commands.command(
        name="game_session-list",
        description="List all game sessions"
    )
    @app_commands.describe(
        status="Filter by status (waiting, active, completed)"
    )
    @app_commands.choices(status=[
        app_commands.Choice(name="All", value="all"),
        app_commands.Choice(name="Waiting", value="waiting"),
        app_commands.Choice(name="Active", value="active"),
        app_commands.Choice(name="Completed", value="completed")
    ])
    @requires_linked_account
    async def list_sessions(
        self,
        interaction: discord.Interaction,
        status: str = "all"
    ) -> None:
        """
        List all game sessions.
        
        Requires linked account.
        
        Args:
            interaction: Discord interaction
            status: Filter by session status
        """
        await interaction.response.defer(ephemeral=True)
        
        if not self._http_session:
            await interaction.followup.send("❌ HTTP session not initialized", ephemeral=True)
            return
        
        player_name = interaction.extras.get('player_name', 'Unknown')
        
        url = f"{self.game_server_url}/game/sessions"
        if status != "all":
            url += f"?status={status}"
        
        try:
            async with self._http_session.get(
                url, 
                headers=self._get_user_headers(interaction)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    sessions = data.get('sessions', [])
                    
                    if not sessions:
                        await interaction.followup.send(
                            f"📋 No sessions found{f' with status: {status}' if status != 'all' else ''}",
                            ephemeral=True
                        )
                        return
                    
                    embed = discord.Embed(
                        title="📋 Game Sessions",
                        description=f"Found {len(sessions)} session(s) • Logged in as **{player_name}**",
                        color=0x5865F2
                    )
                    
                    for session in sessions[:10]:  # Limit to 10 for embed
                        session_status = session.get('status', 'unknown')
                        status_emoji = {
                            'waiting': '⏳',
                            'active': '🎮',
                            'completed': '✅',
                            'cancelled': '❌'
                        }.get(session_status, '❓')
                        
                        embed.add_field(
                            name=f"{status_emoji} {session.get('session_name', 'Unnamed')}",
                            value=(
                                f"ID: `{session.get('session_id', 'N/A')[:8]}...`\n"
                                f"Players: {session.get('player_count', 0)}/{session.get('max_players', 6)}\n"
                                f"Turn: {session.get('turn_number', 1)}"
                            ),
                            inline=True
                        )
                    
                    if len(sessions) > 10:
                        embed.set_footer(text=f"Showing 10 of {len(sessions)} sessions")
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await self._handle_error_response(interaction, response, "list sessions")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to game server: {e}")
            await interaction.followup.send(f"❌ Failed to connect to game server: {e}", ephemeral=True)
        except Exception as e:
            logger.error(f"Unexpected error listing sessions: {e}")
            await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)
    
    @app_commands.command(
        name="game_session-end",
        description="End a game session"
    )
    @app_commands.describe(
        session_id="The session ID to end"
    )
    @requires_linked_account
    async def end_session(
        self,
        interaction: discord.Interaction,
        session_id: str
    ) -> None:
        """
        End a game session.
        
        Requires linked account with admin privileges.
        
        Args:
            interaction: Discord interaction
            session_id: Session ID to end
        """
        await interaction.response.defer(ephemeral=True)
        
        if not self._http_session:
            await interaction.followup.send("❌ HTTP session not initialized", ephemeral=True)
            return
        
        player_name = interaction.extras.get('player_name', 'Unknown')
        url = f"{self.game_server_url}/admin/sessions/{session_id}/end"
        
        try:
            async with self._http_session.post(
                url, 
                headers=self._get_user_headers(interaction)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    embed = discord.Embed(
                        title="✅ Game Session Ended",
                        description=f"Ended by **{player_name}**",
                        color=0xFF6B6B
                    )
                    embed.add_field(name="Session ID", value=f"`{session_id}`", inline=False)
                    embed.add_field(name="Name", value=data.get('session_name', 'Unknown'), inline=True)
                    embed.add_field(name="Final Turn", value=str(data.get('turn_number', '?')), inline=True)
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    logger.info(f"Session {session_id} ended by {interaction.user} ({player_name})")
                else:
                    await self._handle_error_response(interaction, response, "end session")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to game server: {e}")
            await interaction.followup.send(f"❌ Failed to connect to game server: {e}", ephemeral=True)
        except Exception as e:
            logger.error(f"Unexpected error ending session: {e}")
            await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)
    
    @app_commands.command(
        name="game_session-register-channel",
        description="Link this channel to a game session"
    )
    @app_commands.describe(
        session_id="The game session ID to link to this channel"
    )
    @requires_linked_account
    async def register_channel(
        self,
        interaction: discord.Interaction,
        session_id: str
    ) -> None:
        """
        Register current channel to a game session.
        
        Requires linked account with admin privileges.
        
        This:
        1. Binds the channel in game_server database
        2. Registers the channel in the GameChat cog for message forwarding
        
        Args:
            interaction: Discord interaction
            session_id: Game session ID
        """
        await interaction.response.defer(ephemeral=True)
        
        if not self._http_session:
            await interaction.followup.send("❌ HTTP session not initialized", ephemeral=True)
            return
        
        player_name = interaction.extras.get('player_name', 'Unknown')
        channel_id = str(interaction.channel_id)
        
        # Step 1: Bind channel in game_server
        url = f"{self.game_server_url}/admin/sessions/{session_id}/discord-channel"
        payload = {"channel_id": channel_id}
        
        try:
            async with self._http_session.post(
                url, 
                json=payload, 
                headers=self._get_user_headers(interaction)
            ) as response:
                if response.status == 200:
                    # Step 2: Register in GameChat cog for message forwarding
                    game_chat_cog = self.bot.get_cog("game_chat")
                    if game_chat_cog:
                        game_chat_cog.register_channel(interaction.channel_id, session_id)
                    
                    embed = discord.Embed(
                        title="✅ Channel Registered",
                        description=f"Registered by **{player_name}**",
                        color=0x00FF00
                    )
                    embed.add_field(name="Channel", value=f"<#{interaction.channel_id}>", inline=True)
                    embed.add_field(name="Session ID", value=f"`{session_id}`", inline=True)
                    embed.add_field(
                        name="Next Steps",
                        value="Messages in this channel will now be forwarded to the game session.",
                        inline=False
                    )
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    logger.info(f"Channel {channel_id} registered to session {session_id} by {interaction.user} ({player_name})")
                else:
                    await self._handle_error_response(interaction, response, "register channel")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to game server: {e}")
            await interaction.followup.send(f"❌ Failed to connect to game server: {e}", ephemeral=True)
        except Exception as e:
            logger.error(f"Unexpected error registering channel: {e}")
            await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Load the AdminCommands cog."""
    await bot.add_cog(AdminCommands(bot))
