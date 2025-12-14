"""Redis-backed Task Queue with Priority Levels and Dead Letter Queue

Implements a distributed task queue using Redis for:
- Priority-based task scheduling (CRITICAL, HIGH, NORMAL, LOW)
- Dead letter queue for failed tasks
- Task scheduling and retry policies
- Task status tracking and monitoring
"""

import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
import redis
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTERED = "dead_lettered"


@dataclass
class Task:
    """Represents a task in the queue"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    created_at: str = ""
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    queue_name: str = "default"
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        d = asdict(self)
        d['priority'] = self.priority.name
        d['status'] = self.status.value
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary"""
        data['priority'] = TaskPriority[data.get('priority', 'NORMAL')]
        data['status'] = TaskStatus(data.get('status', 'pending'))
        return cls(**data)


class TaskQueue:
    """Redis-backed task queue with priority and dead letter queue support"""
    
    def __init__(self, redis_client: redis.Redis, queue_name: str = "default"):
        """Initialize task queue
        
        Args:
            redis_client: Redis client instance
            queue_name: Name of the queue
        """
        self.redis = redis_client
        self.queue_name = queue_name
        self.dead_letter_queue = f"{queue_name}:dlq"
        self.processing_queue = f"{queue_name}:processing"
        self.priority_queues = {
            TaskPriority.CRITICAL: f"{queue_name}:critical",
            TaskPriority.HIGH: f"{queue_name}:high",
            TaskPriority.NORMAL: f"{queue_name}:normal",
            TaskPriority.LOW: f"{queue_name}:low",
        }
        self.task_store = f"{queue_name}:tasks"
    
    def enqueue(self, task_type: str, payload: Dict[str, Any], 
                priority: TaskPriority = TaskPriority.NORMAL,
                scheduled_at: Optional[datetime] = None,
                max_retries: int = 3) -> Task:
        """Enqueue a new task
        
        Args:
            task_type: Type of task to execute
            payload: Task payload/data
            priority: Task priority level
            scheduled_at: Optional scheduled execution time
            max_retries: Maximum number of retries
            
        Returns:
            Created task
        """
        task = Task(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            queue_name=self.queue_name
        )
        
        if scheduled_at:
            task.scheduled_at = scheduled_at.isoformat()
        
        task_data = json.dumps(task.to_dict())
        
        # Store task metadata
        self.redis.hset(self.task_store, task.task_id, task_data)
        
        # Add to priority queue
        queue_key = self.priority_queues[priority]
        if scheduled_at and scheduled_at > datetime.utcnow():
            # Schedule for later execution
            score = scheduled_at.timestamp()
            self.redis.zadd(f"{queue_key}:scheduled", {task.task_id: score})
        else:
            # Add to immediate queue
            self.redis.lpush(queue_key, task.task_id)
        
        logger.info(f"Task {task.task_id} enqueued with priority {priority.name}")
        return task
    
    def dequeue(self, timeout: int = 0) -> Optional[Task]:
        """Dequeue the next task
        
        Args:
            timeout: Blocking timeout in seconds (0 for non-blocking)
            
        Returns:
            Next task to process or None
        """
        # Check priority queues in order
        for priority in sorted(TaskPriority, key=lambda p: p.value):
            queue_key = self.priority_queues[priority]
            
            # Check scheduled tasks first
            now = datetime.utcnow().timestamp()
            task_ids = self.redis.zrangebyscore(
                f"{queue_key}:scheduled", 0, now, count=1
            )
            
            if task_ids:
                task_id = task_ids[0].decode()
                self.redis.zrem(f"{queue_key}:scheduled", task_id)
                self.redis.lpush(queue_key, task_id)
            
            # Try to get a task
            task_id = self.redis.rpop(queue_key)
            if task_id:
                task_data = self.redis.hget(self.task_store, task_id)
                if task_data:
                    task = Task.from_dict(json.loads(task_data))
                    task.status = TaskStatus.PROCESSING
                    task.started_at = datetime.utcnow().isoformat()
                    self.redis.hset(
                        self.task_store,
                        task.task_id,
                        json.dumps(task.to_dict())
                    )
                    self.redis.lpush(self.processing_queue, task.task_id)
                    return task
        
        return None
    
    def complete(self, task_id: str, result: Optional[Dict[str, Any]] = None):
        """Mark task as completed
        
        Args:
            task_id: Task ID
            result: Optional result data
        """
        task_data = self.redis.hget(self.task_store, task_id)
        if not task_data:
            logger.warning(f"Task {task_id} not found")
            return
        
        task = Task.from_dict(json.loads(task_data))
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow().isoformat()
        task.retry_count = 0
        
        self.redis.hset(
            self.task_store,
            task.task_id,
            json.dumps(task.to_dict())
        )
        self.redis.lrem(self.processing_queue, 0, task_id)
        logger.info(f"Task {task_id} completed successfully")
    
    def fail(self, task_id: str, error_message: str):
        """Handle task failure with retry logic
        
        Args:
            task_id: Task ID
            error_message: Error description
        """
        task_data = self.redis.hget(self.task_store, task_id)
        if not task_data:
            logger.warning(f"Task {task_id} not found")
            return
        
        task = Task.from_dict(json.loads(task_data))
        task.retry_count += 1
        task.error_message = error_message
        
        self.redis.lrem(self.processing_queue, 0, task_id)
        
        if task.retry_count < task.max_retries:
            # Retry with exponential backoff
            task.status = TaskStatus.RETRYING
            backoff_seconds = min(2 ** task.retry_count, 3600)  # Max 1 hour
            retry_time = datetime.utcnow() + timedelta(seconds=backoff_seconds)
            task.scheduled_at = retry_time.isoformat()
            
            self.redis.hset(
                self.task_store,
                task.task_id,
                json.dumps(task.to_dict())
            )
            
            queue_key = self.priority_queues[task.priority]
            score = retry_time.timestamp()
            self.redis.zadd(f"{queue_key}:scheduled", {task.task_id: score})
            logger.warning(f"Task {task_id} failed, retrying in {backoff_seconds}s")
        else:
            # Move to dead letter queue
            task.status = TaskStatus.DEAD_LETTERED
            self.redis.hset(
                self.task_store,
                task.task_id,
                json.dumps(task.to_dict())
            )
            self.redis.lpush(self.dead_letter_queue, task_id)
            logger.error(f"Task {task_id} moved to dead letter queue")
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task details
        
        Args:
            task_id: Task ID
            
        Returns:
            Task or None
        """
        task_data = self.redis.hget(self.task_store, task_id)
        if task_data:
            return Task.from_dict(json.loads(task_data))
        return None
    
    def get_queue_size(self, priority: Optional[TaskPriority] = None) -> int:
        """Get queue size
        
        Args:
            priority: Optional priority level filter
            
        Returns:
            Number of tasks in queue
        """
        if priority:
            queue_key = self.priority_queues[priority]
            return self.redis.llen(queue_key)
        
        total = sum(self.redis.llen(q) for q in self.priority_queues.values())
        return total
    
    def get_dead_letter_tasks(self, limit: int = 100) -> List[Task]:
        """Get tasks in dead letter queue
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of dead lettered tasks
        """
        task_ids = self.redis.lrange(self.dead_letter_queue, 0, limit - 1)
        tasks = []
        for task_id in task_ids:
            task = self.get_task(task_id.decode())
            if task:
                tasks.append(task)
        return tasks
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics
        
        Returns:
            Queue statistics
        """
        return {
            'queue_name': self.queue_name,
            'total_queued': self.get_queue_size(),
            'critical': self.redis.llen(self.priority_queues[TaskPriority.CRITICAL]),
            'high': self.redis.llen(self.priority_queues[TaskPriority.HIGH]),
            'normal': self.redis.llen(self.priority_queues[TaskPriority.NORMAL]),
            'low': self.redis.llen(self.priority_queues[TaskPriority.LOW]),
            'processing': self.redis.llen(self.processing_queue),
            'dead_lettered': self.redis.llen(self.dead_letter_queue),
            'total_tasks': self.redis.hlen(self.task_store),
        }
