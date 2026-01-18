"""
Operations Jobs Service.

Provides introspection into scheduled APScheduler jobs.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


class OpsJobsService:
    """Service for scheduled job introspection."""
    
    # Job type detection based on job ID prefix
    JOB_TYPE_PREFIXES = {
        "chat_broadcast_": "ChatBroadcastJob",
        "phase_transition_": "PhaseTransitionJob",
    }
    
    @classmethod
    def get_all_jobs(cls) -> Dict[str, Any]:
        """
        Get all scheduled jobs with details.
        
        Returns:
            Dict with total count, job type breakdown, and job list
        """
        from app import scheduler
        
        jobs = scheduler.get_jobs()
        job_list = []
        type_counts = {}
        
        for job in jobs:
            job_info = cls._parse_job(job)
            job_list.append(job_info)
            
            # Count by type
            job_type = job_info["type"]
            type_counts[job_type] = type_counts.get(job_type, 0) + 1
        
        return {
            "total_jobs": len(jobs),
            "job_types": type_counts,
            "jobs": job_list,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }
    
    @classmethod
    def get_job_by_id(cls, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific job by ID.
        
        Args:
            job_id: The job ID to look up
        
        Returns:
            Job info dict or None if not found
        """
        from app import scheduler
        
        job = scheduler.get_job(job_id)
        
        if not job:
            return None
        
        return cls._parse_job(job)
    
    @classmethod
    def get_jobs_by_session(cls, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all jobs for a specific session.
        
        Args:
            session_id: The session ID to filter by
        
        Returns:
            List of job info dicts
        """
        from app import scheduler
        
        jobs = scheduler.get_jobs()
        result = []
        
        for job in jobs:
            if session_id in job.id:
                result.append(cls._parse_job(job))
        
        return result
    
    @classmethod
    def _parse_job(cls, job) -> Dict[str, Any]:
        """
        Parse an APScheduler job into a dict.
        
        Args:
            job: APScheduler Job object
        
        Returns:
            Dict with job details
        """
        # Detect job type from ID
        job_type = "Unknown"
        session_id = None
        
        for prefix, type_name in cls.JOB_TYPE_PREFIXES.items():
            if job.id.startswith(prefix):
                job_type = type_name
                session_id = job.id[len(prefix):]
                break
        
        # Get trigger info
        trigger_type = "unknown"
        interval_minutes = None
        
        trigger = job.trigger
        trigger_class = trigger.__class__.__name__
        
        if trigger_class == "IntervalTrigger":
            trigger_type = "interval"
            # Extract interval in minutes
            if hasattr(trigger, 'interval'):
                interval_minutes = int(trigger.interval.total_seconds() / 60)
        elif trigger_class == "DateTrigger":
            trigger_type = "date"
        elif trigger_class == "CronTrigger":
            trigger_type = "cron"
        
        # Get next run time
        next_run = None
        if job.next_run_time:
            next_run = job.next_run_time.isoformat()
        
        result = {
            "id": job.id,
            "type": job_type,
            "trigger": trigger_type,
            "next_run": next_run,
        }
        
        if session_id:
            result["session_id"] = session_id
        
        if interval_minutes:
            result["interval_minutes"] = interval_minutes
        
        return result

