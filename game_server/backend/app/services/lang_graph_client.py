"""
Lang Graph Client.

HTTP client for pushing events to lang_graph_server.
Uses fire-and-forget pattern to avoid blocking game_server responses.
"""

import os
import logging
import threading

import httpx

logger = logging.getLogger(__name__)


class LangGraphClient:
    """HTTP client for pushing events to lang_graph_server."""
    
    BASE_URL = os.getenv("LANG_GRAPH_SERVER_URL", "http://localhost:8000")
    
    @staticmethod
    def push_chat_event(
        session_id: str,
        sender_id: str,
        platform: str,
        content: str,
        sender_is_llm: bool = False
    ) -> None:
        """
        Push chat message to lang_graph_server (fire-and-forget).
        
        This method spawns a background thread to POST the event,
        allowing the caller to return immediately without waiting.
        
        Args:
            session_id: Game session ID
            sender_id: Sender's display name
            platform: Source platform (discord, slack, etc.)
            content: Message content
            sender_is_llm: Whether sender is an LLM agent
        """
        def _post():
            try:
                response = httpx.post(
                    f"{LangGraphClient.BASE_URL}/coup-events/event",
                    json={
                        "event_type": "chat_message",
                        "source_platform": platform,
                        "sender_id": sender_id,
                        "sender_is_llm": sender_is_llm,
                        "game_id": session_id,
                        "broadcast_to_all_agents": True,
                        "payload": {"content": content}
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    logger.debug(
                        f"[LangGraphClient] Pushed chat event for session {session_id}"
                    )
                else:
                    logger.warning(
                        f"[LangGraphClient] Push returned {response.status_code}: "
                        f"{response.text[:100]}"
                    )
                    
            except httpx.ConnectError as e:
                logger.warning(f"[LangGraphClient] Connection failed: {e}")
            except httpx.TimeoutException:
                logger.warning("[LangGraphClient] Request timed out")
            except Exception as e:
                logger.error(f"[LangGraphClient] Push failed: {e}")
        
        # Fire and forget via daemon thread
        thread = threading.Thread(target=_post, daemon=True)
        thread.start()
        logger.debug(f"[LangGraphClient] Spawned push thread for session {session_id}")

