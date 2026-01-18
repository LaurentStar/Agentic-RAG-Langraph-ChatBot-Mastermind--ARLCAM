"""
Jobs Registry.

All scheduled jobs in the Coup game server are registered here.
This provides a single source of truth for discovering recurring tasks.

┌──────────────────────────────────────────────────────────────────────────────┐
│ JOB REGISTRY                                                                 │
├─────────────────────┬──────────────────┬─────────────────────────────────────┤
│ Job Class           │ Trigger          │ Description                         │
├─────────────────────┼──────────────────┼─────────────────────────────────────┤
│ ChatBroadcastJob    │ interval (5 min) │ Push chat messages to bot endpoints │
│ PhaseTransitionJob  │ date (one-shot)  │ Advance game phase after duration   │
│ EndingPhaseJob      │ date (one-shot)  │ Complete session after ENDING phase │
└─────────────────────┴──────────────────┴─────────────────────────────────────┘

Usage:
    from app.jobs import ChatBroadcastJob, PhaseTransitionJob, EndingPhaseJob
    
    # Schedule a recurring chat broadcast
    job_id = ChatBroadcastJob.schedule(session_id, interval_minutes=5)
    
    # Cancel it
    ChatBroadcastJob.cancel(session_id)
    
    # Schedule a one-time phase transition
    job_id = PhaseTransitionJob.schedule(session_id)
    
    # Schedule session completion after ENDING phase
    job_id = EndingPhaseJob.schedule(session_id)
    
    # Cancel ending (e.g., when rematch is requested)
    EndingPhaseJob.cancel(session_id)
"""

from app.jobs.chat_broadcast_job import ChatBroadcastJob
from app.jobs.phase_transition_job import PhaseTransitionJob
from app.jobs.ending_phase_job import EndingPhaseJob

__all__ = [
    "ChatBroadcastJob",
    "PhaseTransitionJob",
    "EndingPhaseJob",
]

