"""
Phase 11C: Queue Worker

Background worker process that monitors the queue and
starts project processing when capacity is available.
"""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional, Callable, Any
import traceback

from sqlalchemy.orm import Session

from models.database import get_db, SessionLocal
from models.project import Project, ProjectStatus
from task_queue.manager import QueueManager, get_queue_manager, QueueItem
from config.settings import get_settings


# Worker configuration
POLL_INTERVAL = 5  # seconds
SHUTDOWN_TIMEOUT = 30  # seconds


class QueueWorker:
    """
    Background worker that processes the project queue.
    
    Monitors the queue and starts project pipelines when
    capacity becomes available.
    """
    
    def __init__(
        self,
        pipeline_executor: Optional[Callable[[str, Session], Any]] = None
    ):
        """
        Initialize the queue worker.
        
        Args:
            pipeline_executor: Function to execute pipeline for a project.
                              Should accept (project_id, db_session).
                              If None, uses default orchestration pipeline.
        """
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._current_tasks: dict[str, asyncio.Task] = {}
        self._queue_manager = get_queue_manager()
        self._pipeline_executor = pipeline_executor
        self._stats = {
            "projects_processed": 0,
            "projects_failed": 0,
            "started_at": None,
            "last_poll": None
        }
    
    async def start(self):
        """
        Start the worker process.
        
        Runs indefinitely, polling the queue for new projects.
        """
        self._running = True
        self._stats["started_at"] = datetime.utcnow().isoformat()
        
        print(f"[QueueWorker] Starting at {self._stats['started_at']}")
        print(f"[QueueWorker] Poll interval: {POLL_INTERVAL}s")
        print(f"[QueueWorker] Max concurrent: {self._queue_manager._max_concurrent}")
        
        # Set up signal handlers
        self._setup_signal_handlers()
        
        while self._running:
            try:
                self._stats["last_poll"] = datetime.utcnow().isoformat()
                
                # Try to dequeue and start projects
                await self._process_queue()
                
                # Clean up completed tasks
                self._cleanup_tasks()
                
                # Wait before next poll
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=POLL_INTERVAL
                    )
                    # Shutdown was signaled
                    break
                except asyncio.TimeoutError:
                    # Normal timeout, continue polling
                    pass
                    
            except Exception as e:
                print(f"[QueueWorker] Error in main loop: {e}")
                traceback.print_exc()
                await asyncio.sleep(POLL_INTERVAL)
        
        # Graceful shutdown
        await self._shutdown()
    
    async def _process_queue(self):
        """Process items from the queue"""
        while True:
            # Check if we have capacity
            active_count = len(self._current_tasks)
            max_concurrent = self._queue_manager._max_concurrent
            
            if active_count >= max_concurrent:
                return
            
            # Try to dequeue a project
            item = self._queue_manager.dequeue_project()
            if item is None:
                return
            
            print(f"[QueueWorker] Dequeued project: {item.project_id}")
            print(f"[QueueWorker] Priority: {item.priority.value}")
            
            # Start project processing
            task = asyncio.create_task(
                self._execute_project(item)
            )
            self._current_tasks[item.project_id] = task
    
    async def _execute_project(self, item: QueueItem):
        """
        Execute the pipeline for a project.
        
        Args:
            item: Queue item containing project info
        """
        project_id = item.project_id
        db = SessionLocal()
        
        try:
            # Update project status
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.status = ProjectStatus.INTAKE
                db.commit()
            
            # Execute pipeline
            if self._pipeline_executor:
                await self._pipeline_executor(project_id, db)
            else:
                # Default: use PipelineExecutor
                from orchestration.executor import PipelineExecutor
                executor = PipelineExecutor(db_session=db)
                await executor.execute(
                    project_id=project_id,
                    brief=project.brief or "",
                    cost_profile=project.cost_profile.value if project.cost_profile else "balanced",
                    requirements=project.requirements or {},
                )
            
            self._stats["projects_processed"] += 1
            print(f"[QueueWorker] Completed project: {project_id}")
            
        except Exception as e:
            self._stats["projects_failed"] += 1
            print(f"[QueueWorker] Failed project {project_id}: {e}")
            traceback.print_exc()
            
            # Update project status to failed
            try:
                project = db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.status = ProjectStatus.FAILED
                    if not project.agent_outputs:
                        project.agent_outputs = {}
                    project.agent_outputs["error"] = str(e)
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()
            # Mark as completed in queue
            self._queue_manager.complete_project(project_id)
    
    def _cleanup_tasks(self):
        """Remove completed tasks from tracking"""
        completed = [
            pid for pid, task in self._current_tasks.items()
            if task.done()
        ]
        for pid in completed:
            del self._current_tasks[pid]
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            print(f"[QueueWorker] Received signal {sig}, shutting down...")
            self._running = False
            self._shutdown_event.set()
        
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except Exception:
            # Signal handlers may not work in all environments
            pass
    
    async def _shutdown(self):
        """Graceful shutdown: wait for current tasks to complete"""
        print(f"[QueueWorker] Shutting down, waiting for {len(self._current_tasks)} tasks...")
        
        if self._current_tasks:
            # Wait for current tasks with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._current_tasks.values(), return_exceptions=True),
                    timeout=SHUTDOWN_TIMEOUT
                )
            except asyncio.TimeoutError:
                print(f"[QueueWorker] Shutdown timeout, cancelling tasks...")
                for task in self._current_tasks.values():
                    task.cancel()
        
        print(f"[QueueWorker] Shutdown complete")
        print(f"[QueueWorker] Stats: {self._stats}")
    
    def stop(self):
        """Signal the worker to stop"""
        self._running = False
        self._shutdown_event.set()
    
    def get_stats(self) -> dict:
        """Get worker statistics"""
        return {
            **self._stats,
            "active_tasks": len(self._current_tasks),
            "active_project_ids": list(self._current_tasks.keys()),
            "running": self._running
        }


async def start_worker(pipeline_executor: Optional[Callable] = None):
    """
    Start the queue worker.
    
    This is the main entry point for running the worker as a standalone process.
    
    Args:
        pipeline_executor: Optional custom pipeline executor function
    """
    worker = QueueWorker(pipeline_executor)
    await worker.start()


if __name__ == "__main__":
    # Run as standalone process
    asyncio.run(start_worker())
