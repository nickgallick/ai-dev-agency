"""
Phase 11C: Project Queue Manager

Redis-based FIFO queue with priority levels and position tracking.
"""

import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import redis

from backend.config.settings import get_settings


class QueuePriority(str, Enum):
    URGENT = "urgent"       # Immediate processing
    NORMAL = "normal"       # Standard FIFO
    BACKGROUND = "background"  # Yields to higher priorities


# Priority weights for sorting (lower = higher priority)
PRIORITY_WEIGHTS = {
    QueuePriority.URGENT: 0,
    QueuePriority.NORMAL: 1000000000,  # 1 billion offset
    QueuePriority.BACKGROUND: 2000000000,  # 2 billion offset
}

# Queue key names
QUEUE_KEY = "project_queue"
ACTIVE_KEY = "project_queue:active"
METADATA_KEY = "project_queue:meta"

# Default max concurrent projects
DEFAULT_MAX_CONCURRENT = 2


class QueueItem:
    """Represents an item in the queue"""
    
    def __init__(
        self,
        project_id: str,
        priority: QueuePriority = QueuePriority.NORMAL,
        queued_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.project_id = project_id
        self.priority = priority
        self.queued_at = queued_at or datetime.utcnow()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "priority": self.priority.value,
            "queued_at": self.queued_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueItem":
        return cls(
            project_id=data["project_id"],
            priority=QueuePriority(data["priority"]),
            queued_at=datetime.fromisoformat(data["queued_at"]),
            metadata=data.get("metadata", {})
        )
    
    def get_score(self) -> float:
        """
        Calculate sort score for priority queue.
        Lower score = higher priority.
        
        Score = priority_weight + timestamp_seconds
        This ensures FIFO within the same priority level.
        """
        priority_weight = PRIORITY_WEIGHTS[self.priority]
        timestamp = self.queued_at.timestamp()
        return priority_weight + timestamp


class QueueManager:
    """
    Redis-based project queue manager with priority support.
    """
    
    _instance: Optional["QueueManager"] = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        settings = get_settings()
        self._redis: Optional[redis.Redis] = None
        self._connected = False
        self._local_queue: List[QueueItem] = []  # Fallback
        self._local_active: Dict[str, QueueItem] = {}  # Fallback
        self._max_concurrent = getattr(settings, 'max_concurrent_projects', DEFAULT_MAX_CONCURRENT)
        
        try:
            self._redis = redis.Redis(
                host=getattr(settings, 'redis_host', 'localhost'),
                port=getattr(settings, 'redis_port', 6379),
                db=getattr(settings, 'redis_db', 0),
                password=getattr(settings, 'redis_password', None),
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            self._redis.ping()
            self._connected = True
        except (redis.ConnectionError, redis.TimeoutError) as e:
            print(f"Redis connection failed for queue: {e}")
            self._redis = None
            self._connected = False
        
        self._initialized = True
    
    @property
    def connected(self) -> bool:
        return self._connected and self._redis is not None
    
    def enqueue_project(
        self,
        project_id: str,
        priority: QueuePriority = QueuePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, float]:
        """
        Add a project to the queue.
        
        Args:
            project_id: UUID of the project
            priority: Queue priority level
            metadata: Additional metadata (project name, type, etc.)
            
        Returns:
            Tuple of (position_in_queue, estimated_wait_seconds)
        """
        item = QueueItem(
            project_id=project_id,
            priority=priority,
            queued_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        if self._connected and self._redis:
            try:
                # Add to sorted set with score
                self._redis.zadd(QUEUE_KEY, {project_id: item.get_score()})
                
                # Store metadata
                self._redis.hset(METADATA_KEY, project_id, json.dumps(item.to_dict()))
                
                # Get position
                position = self._get_position_redis(project_id)
                estimated_wait = self._estimate_wait_redis(position)
                
                return position, estimated_wait
            except redis.RedisError as e:
                print(f"Redis enqueue error: {e}")
        
        # Fallback to local
        self._local_queue.append(item)
        self._local_queue.sort(key=lambda x: x.get_score())
        
        position = self._get_position_local(project_id)
        estimated_wait = self._estimate_wait_local(position)
        
        return position, estimated_wait
    
    def dequeue_project(self) -> Optional[QueueItem]:
        """
        Get the next project from the queue (if under concurrency limit).
        
        Returns:
            QueueItem if available, None otherwise
        """
        # Check concurrency limit
        active_count = self.get_active_count()
        if active_count >= self._max_concurrent:
            return None
        
        if self._connected and self._redis:
            try:
                # Get the lowest-scored item (highest priority, oldest in its tier)
                items = self._redis.zrange(QUEUE_KEY, 0, 0, withscores=True)
                if not items:
                    return None
                
                project_id, score = items[0]
                
                # Remove from queue
                self._redis.zrem(QUEUE_KEY, project_id)
                
                # Get metadata
                meta_json = self._redis.hget(METADATA_KEY, project_id)
                if meta_json:
                    item = QueueItem.from_dict(json.loads(meta_json))
                    self._redis.hdel(METADATA_KEY, project_id)
                else:
                    item = QueueItem(project_id=project_id)
                
                # Mark as active
                self._redis.hset(ACTIVE_KEY, project_id, json.dumps({
                    "started_at": datetime.utcnow().isoformat(),
                    "item": item.to_dict()
                }))
                
                return item
            except redis.RedisError as e:
                print(f"Redis dequeue error: {e}")
        
        # Fallback to local
        if not self._local_queue:
            return None
        
        item = self._local_queue.pop(0)
        self._local_active[item.project_id] = item
        return item
    
    def complete_project(self, project_id: str):
        """
        Mark a project as completed and remove from active list.
        
        Args:
            project_id: UUID of the completed project
        """
        if self._connected and self._redis:
            try:
                self._redis.hdel(ACTIVE_KEY, project_id)
                return
            except redis.RedisError:
                pass
        
        # Fallback
        self._local_active.pop(project_id, None)
    
    def get_queue_position(self, project_id: str) -> Optional[int]:
        """
        Get the current position of a project in the queue.
        
        Args:
            project_id: UUID of the project
            
        Returns:
            Position (1-based) or None if not in queue
        """
        if self._connected and self._redis:
            return self._get_position_redis(project_id)
        return self._get_position_local(project_id)
    
    def _get_position_redis(self, project_id: str) -> Optional[int]:
        """Get position from Redis"""
        try:
            rank = self._redis.zrank(QUEUE_KEY, project_id)
            return rank + 1 if rank is not None else None
        except redis.RedisError:
            return None
    
    def _get_position_local(self, project_id: str) -> Optional[int]:
        """Get position from local queue"""
        for i, item in enumerate(self._local_queue):
            if item.project_id == project_id:
                return i + 1
        return None
    
    def get_estimated_wait(self, project_id: str) -> Optional[float]:
        """
        Get estimated wait time in seconds.
        
        Args:
            project_id: UUID of the project
            
        Returns:
            Estimated seconds until processing starts
        """
        position = self.get_queue_position(project_id)
        if position is None:
            return None
        
        if self._connected:
            return self._estimate_wait_redis(position)
        return self._estimate_wait_local(position)
    
    def _estimate_wait_redis(self, position: int) -> float:
        """Estimate wait time based on position and average processing time"""
        # Get average processing time from completed projects
        avg_time = 300  # Default 5 minutes
        
        # Calculate: (position / max_concurrent) * avg_time
        return (position / self._max_concurrent) * avg_time
    
    def _estimate_wait_local(self, position: int) -> float:
        """Estimate wait time locally"""
        avg_time = 300  # Default 5 minutes
        return (position / self._max_concurrent) * avg_time
    
    def reprioritize(
        self,
        project_id: str,
        new_priority: QueuePriority
    ) -> bool:
        """
        Change the priority of a queued project.
        
        Args:
            project_id: UUID of the project
            new_priority: New priority level
            
        Returns:
            True if successful
        """
        if self._connected and self._redis:
            try:
                # Get current metadata
                meta_json = self._redis.hget(METADATA_KEY, project_id)
                if not meta_json:
                    return False
                
                item = QueueItem.from_dict(json.loads(meta_json))
                item.priority = new_priority
                
                # Update score and metadata
                self._redis.zadd(QUEUE_KEY, {project_id: item.get_score()})
                self._redis.hset(METADATA_KEY, project_id, json.dumps(item.to_dict()))
                
                return True
            except redis.RedisError as e:
                print(f"Redis reprioritize error: {e}")
                return False
        
        # Fallback to local
        for item in self._local_queue:
            if item.project_id == project_id:
                item.priority = new_priority
                self._local_queue.sort(key=lambda x: x.get_score())
                return True
        
        return False
    
    def remove_from_queue(self, project_id: str) -> bool:
        """
        Remove a project from the queue.
        
        Args:
            project_id: UUID of the project
            
        Returns:
            True if removed
        """
        if self._connected and self._redis:
            try:
                removed = self._redis.zrem(QUEUE_KEY, project_id)
                self._redis.hdel(METADATA_KEY, project_id)
                return bool(removed)
            except redis.RedisError:
                pass
        
        # Fallback
        for i, item in enumerate(self._local_queue):
            if item.project_id == project_id:
                self._local_queue.pop(i)
                return True
        return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get full queue status.
        
        Returns:
            Queue status with counts, active projects, and queue contents
        """
        if self._connected and self._redis:
            try:
                queue_length = self._redis.zcard(QUEUE_KEY)
                active_projects = self._redis.hgetall(ACTIVE_KEY)
                
                # Get all queued items
                all_items = self._redis.zrange(QUEUE_KEY, 0, -1, withscores=True)
                queue_items = []
                
                for project_id, score in all_items:
                    meta_json = self._redis.hget(METADATA_KEY, project_id)
                    if meta_json:
                        item = QueueItem.from_dict(json.loads(meta_json))
                        queue_items.append({
                            "project_id": project_id,
                            "priority": item.priority.value,
                            "queued_at": item.queued_at.isoformat(),
                            "position": all_items.index((project_id, score)) + 1,
                            "estimated_wait_seconds": self._estimate_wait_redis(
                                all_items.index((project_id, score)) + 1
                            )
                        })
                
                return {
                    "queue_length": queue_length,
                    "active_count": len(active_projects),
                    "max_concurrent": self._max_concurrent,
                    "has_capacity": len(active_projects) < self._max_concurrent,
                    "queue_items": queue_items,
                    "active_projects": [
                        json.loads(v) for v in active_projects.values()
                    ]
                }
            except redis.RedisError as e:
                return {"error": str(e), "connected": False}
        
        # Fallback to local
        return {
            "queue_length": len(self._local_queue),
            "active_count": len(self._local_active),
            "max_concurrent": self._max_concurrent,
            "has_capacity": len(self._local_active) < self._max_concurrent,
            "queue_items": [
                {
                    "project_id": item.project_id,
                    "priority": item.priority.value,
                    "queued_at": item.queued_at.isoformat(),
                    "position": i + 1,
                    "estimated_wait_seconds": self._estimate_wait_local(i + 1)
                }
                for i, item in enumerate(self._local_queue)
            ],
            "active_projects": [
                item.to_dict() for item in self._local_active.values()
            ]
        }
    
    def get_active_count(self) -> int:
        """Get number of currently active projects"""
        if self._connected and self._redis:
            try:
                return self._redis.hlen(ACTIVE_KEY)
            except redis.RedisError:
                pass
        return len(self._local_active)
    
    def clear_queue(self):
        """Clear the entire queue (admin operation)"""
        if self._connected and self._redis:
            try:
                self._redis.delete(QUEUE_KEY)
                self._redis.delete(METADATA_KEY)
                return
            except redis.RedisError:
                pass
        
        self._local_queue = []


def get_queue_manager() -> QueueManager:
    """Get the singleton QueueManager instance"""
    return QueueManager()
