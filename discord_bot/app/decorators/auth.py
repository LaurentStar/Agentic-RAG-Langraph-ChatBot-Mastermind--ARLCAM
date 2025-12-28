"""
Authentication Decorators for Discord Slash Commands.

Provides decorators to enforce account linking requirements
for Discord users executing slash commands.
"""

import functools
import logging
from typing import Callable, Any

import discord

from app.services.token_cache_service import TokenCacheService

logger = logging.getLogger("discord_bot")


def requires_linked_account(func: Callable) -> Callable:
    """
    Decorator that ensures the Discord user has a linked game account.
    
    If the user has a linked account:
    - Fetches/caches their JWT token
    - Stores token in interaction.extras['jwt_token']
    - Stores player name in interaction.extras['player_name']
    - Proceeds with the command
    
    If the user does NOT have a linked account:
    - Sends an ephemeral message with login instructions
    - Does NOT execute the command
    
    Usage:
        @app_commands.command(name="my-command", description="...")
        @requires_linked_account
        async def my_command(self, interaction: discord.Interaction):
            token = interaction.extras.get('jwt_token')
            # Use token for authenticated requests
    
    Note: This decorator must be applied AFTER @app_commands.command
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        # Find the interaction in args (self, interaction, ...) or kwargs
        interaction: discord.Interaction = None
        self_arg = None
        
        for i, arg in enumerate(args):
            if isinstance(arg, discord.Interaction):
                interaction = arg
                break
            elif hasattr(arg, 'bot'):  # This is 'self' (the cog)
                self_arg = arg
        
        if interaction is None:
            interaction = kwargs.get('interaction')
        
        if interaction is None:
            logger.error("requires_linked_account: No interaction found in command")
            raise ValueError("No interaction found - decorator misconfigured")
        
        # Get Discord user ID
        discord_user_id = str(interaction.user.id)
        
        # Check token cache / fetch from game server
        token, error = await TokenCacheService.get_token(discord_user_id)
        
        if error == "not_linked":
            # User needs to link their account
            login_url = TokenCacheService.get_oauth_login_url()
            
            embed = discord.Embed(
                title="🔗 Account Not Linked",
                description=(
                    "You need to link your Discord account to play.\n\n"
                    "**Click the button below to link your account.**"
                ),
                color=0xFF9500
            )
            embed.add_field(
                name="Why link?",
                value="Linking lets you play Coup across Discord and other platforms with a single account.",
                inline=False
            )
            
            # Create button for OAuth login
            view = LinkAccountView(login_url)
            
            # Respond to interaction
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            logger.info(f"Account link required for Discord user {interaction.user} ({discord_user_id})")
            return  # Don't execute the command
        
        elif error:
            # Some other error (network, etc.)
            if interaction.response.is_done():
                await interaction.followup.send(
                    f"❌ Authentication error: {error}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ Authentication error: {error}",
                    ephemeral=True
                )
            
            logger.error(f"Auth error for Discord user {discord_user_id}: {error}")
            return  # Don't execute the command
        
        # Success - inject token into interaction extras
        if not hasattr(interaction, 'extras') or interaction.extras is None:
            # Create extras dict if it doesn't exist
            object.__setattr__(interaction, 'extras', {})
        
        interaction.extras['jwt_token'] = token
        interaction.extras['player_name'] = TokenCacheService.get_cached_player_name(discord_user_id)
        
        logger.debug(f"Auth success for Discord user {discord_user_id}")
        
        # Execute the original command
        return await func(*args, **kwargs)
    
    return wrapper


class LinkAccountView(discord.ui.View):
    """View with button to link Discord account."""
    
    def __init__(self, login_url: str):
        super().__init__(timeout=300)  # 5 minute timeout
        
        # Add link button
        self.add_item(
            discord.ui.Button(
                label="Link Account",
                url=login_url,
                style=discord.ButtonStyle.link,
                emoji="🔗"
            )
        )

