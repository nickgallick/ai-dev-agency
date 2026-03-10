"""
Phase 11C: Project Queue & Concurrency

Redis-based FIFO queue with priority levels:
- urgent: Immediate processing
- normal: Standard FIFO
- background: Yields to urgent/normal

Max 2 concurrent projects (configurable).
"""

from .manager import QueueManager, get_queue_manager, QueuePriority
from .worker import QueueWorker, start_worker

__all__ = [
    "QueueManager",
    "get_queue_manager",
    "QueuePriority",
    "QueueWorker",
    "start_worker"
]
