"""
Lang Graph Client.

HTTP client for pushing events to lang_graph_server.
Uses fire-and-forget pattern to avoid blocking game_server responses.
"""

import os
import logging
import threading

import httpx
from flask import current_app

from app.services.logging_service import GameServerLoggingService

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
        # Capture Flask app BEFORE spawning thread (while in request context)
        # This allows the background thread to use app.app_context() for DB ops
        app = current_app._get_current_object()
        
        def _post():
            url = f"{LangGraphClient.BASE_URL}/coup-events/event"
            payload = {
                "event_type": "chat_message",
                "source_platform": platform,
                "sender_id": sender_id,
                "sender_is_llm": sender_is_llm,
                "game_id": session_id,
                "broadcast_to_all_agents": True,
                "payload": {"content": content}
            }
            
            logger.info(
                f"[CHAT-FLOW] GameServer → LangGraph: session={session_id} "
                f"sender={sender_id} event_type=chat_message"
            )
            
            try:
                response = httpx.post(url, json=payload, timeout=5.0)
                
                if response.status_code == 200:
                    response_preview = response.text[:100] if response.text else "(empty)"
                    logger.info(
                        f"[CHAT-FLOW] LangGraph accepted: session={session_id} "
                        f"status=200 response={response_preview}"
                    )
                    # Log success to database (with app context)
                    with app.app_context():
                        GameServerLoggingService.log_langgraph_push(
                            session_id=session_id,
                            sender_id=sender_id,
                            status="success",
                            response=response.text[:200] if response.text else None
                        )
                else:
                    logger.warning(
                        f"[CHAT-FLOW] LangGraph rejected: session={session_id} "
                        f"status={response.status_code} response={response.text[:100]}"
                    )
                    # Log failure to database (with app context)
                    with app.app_context():
                        GameServerLoggingService.log_langgraph_push(
                            session_id=session_id,
                            sender_id=sender_id,
                            status="failed",
                            error=f"HTTP {response.status_code}: {response.text[:100]}"
                        )
                    
            except httpx.ConnectError as e:
                logger.error(
                    f"[CHAT-FLOW] LangGraph unreachable: session={session_id} error={e}"
                )
                with app.app_context():
                    GameServerLoggingService.log_langgraph_push(
                        session_id=session_id,
                        sender_id=sender_id,
                        status="unreachable",
                        error=str(e)
                    )
            except httpx.TimeoutException:
                logger.warning(
                    f"[CHAT-FLOW] LangGraph timeout: session={session_id}"
                )
                with app.app_context():
                    GameServerLoggingService.log_langgraph_push(
                        session_id=session_id,
                        sender_id=sender_id,
                        status="timeout",
                        error="Request timed out after 5s"
                    )
            except Exception as e:
                logger.error(
                    f"[CHAT-FLOW] LangGraph error: session={session_id} error={e}"
                )
                with app.app_context():
                    GameServerLoggingService.log_langgraph_push(
                        session_id=session_id,
                        sender_id=sender_id,
                        status="failed",
                        error=str(e)
                    )
        
        # Fire and forget via daemon thread
        thread = threading.Thread(target=_post, daemon=True)
        thread.start()
        logger.debug(f"[CHAT-FLOW] Spawned push thread for session {session_id}")
    
    @staticmethod
    def register_agents(
        session_id: str,
        agents: list,
        players_alive: list = None
    ) -> dict:
        """
        Register LLM agents with lang_graph_server.
        
        Called when a game session starts to create agent instances
        in the lang_graph_server's in-memory registry.
        
        This is a synchronous call (not fire-and-forget) because we need
        to know if registration succeeded before proceeding.
        
        Args:
            session_id: Game session ID
            agents: List of dicts with agent info:
                    [{"agent_id": "...", "play_style": "...", "personality": "..."}]
            players_alive: List of all player display names in the session
            
        Returns:
            Response dict from lang_graph_server or error dict
        """
        url = f"{LangGraphClient.BASE_URL}/coup-events/agents/{session_id}/register"
        
        # Build agent configs
        agent_configs = []
        for agent in agents:
            config = {
                "agent_id": agent.get("agent_id") or agent.get("display_name"),
                "play_style": agent.get("play_style", "balanced"),
                "personality": agent.get("personality", "friendly"),
                "coins": agent.get("coins", 2),
            }
            if players_alive:
                config["players_alive"] = players_alive
            agent_configs.append(config)
        
        payload = {"agents": agent_configs}
        
        logger.info(
            f"[AGENT-REG] Registering {len(agent_configs)} agents for session {session_id}"
        )
        
        try:
            response = httpx.post(url, json=payload, timeout=10.0)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"[AGENT-REG] Registration successful: session={session_id} "
                    f"registered={result.get('agents_registered', 0)}"
                )
                return result
            else:
                logger.error(
                    f"[AGENT-REG] Registration failed: session={session_id} "
                    f"status={response.status_code} response={response.text[:100]}"
                )
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:100]}",
                }
                
        except httpx.ConnectError as e:
            logger.error(f"[AGENT-REG] LangGraph unreachable: {e}")
            return {"success": False, "error": f"LangGraph unreachable: {e}"}
        except httpx.TimeoutException:
            logger.error("[AGENT-REG] LangGraph request timed out")
            return {"success": False, "error": "Request timed out"}
        except Exception as e:
            logger.error(f"[AGENT-REG] Unexpected error: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def cleanup_agents(session_id: str) -> dict:
        """
        Remove agents for a game session from lang_graph_server.
        
        Called when a game session ends to free memory.
        
        Args:
            session_id: Game session ID
            
        Returns:
            Response dict from lang_graph_server or error dict
        """
        url = f"{LangGraphClient.BASE_URL}/coup-events/agents/{session_id}"
        
        logger.info(f"[AGENT-REG] Cleaning up agents for session {session_id}")
        
        try:
            response = httpx.delete(url, timeout=10.0)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"[AGENT-REG] Cleanup successful: session={session_id} "
                    f"removed={result.get('agents_removed', 0)}"
                )
                return result
            else:
                logger.warning(
                    f"[AGENT-REG] Cleanup failed: session={session_id} "
                    f"status={response.status_code}"
                )
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                }
                
        except httpx.ConnectError as e:
            logger.warning(f"[AGENT-REG] LangGraph unreachable for cleanup: {e}")
            return {"success": False, "error": f"LangGraph unreachable: {e}"}
        except Exception as e:
            logger.warning(f"[AGENT-REG] Cleanup error: {e}")
            return {"success": False, "error": str(e)}

