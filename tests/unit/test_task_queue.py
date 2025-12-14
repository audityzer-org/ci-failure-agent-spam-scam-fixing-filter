"""Unit tests for TaskQueue implementation"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import json

from src.task_queue import TaskQueue, Task, TaskPriority, TaskStatus


@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    return MagicMock()


@pytest.fixture
def task_queue(mock_redis):
    """Create a TaskQueue instance with mock Redis"""
    return TaskQueue(mock_redis, queue_name="test")


class TestTask:
    """Test Task dataclass"""
    
    def test_task_creation(self):
        """Test creating a task"""
        task = Task(
            task_id="123",
            task_type="process",
            payload={"data": "test"}
        )
        
        assert task.task_id == "123"
        assert task.task_type == "process"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.NORMAL
    
    def test_task_to_dict(self):
        """Test converting task to dictionary"""
        task = Task(
            task_id="123",
            task_type="process",
            payload={"data": "test"},
            priority=TaskPriority.HIGH
        )
        
        d = task.to_dict()
        assert d['task_id'] == "123"
        assert d['priority'] == "HIGH"
        assert d['status'] == "pending"
    
    def test_task_from_dict(self):
        """Test creating task from dictionary"""
        data = {
            'task_id': '123',
            'task_type': 'process',
            'payload': {'data': 'test'},
            'priority': 'HIGH',
            'status': 'pending'
        }
        
        task = Task.from_dict(data)
        assert task.task_id == '123'
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING


class TestTaskQueue:
    """Test TaskQueue functionality"""
    
    def test_enqueue_task(self, task_queue, mock_redis):
        """Test enqueueing a task"""
        payload = {"data": "test"}
        task = task_queue.enqueue(
            "process",
            payload,
            priority=TaskPriority.HIGH
        )
        
        assert task.task_id is not None
        assert task.task_type == "process"
        assert task.priority == TaskPriority.HIGH
        assert mock_redis.hset.called
        assert mock_redis.lpush.called
    
    def test_enqueue_scheduled_task(self, task_queue, mock_redis):
        """Test enqueueing a scheduled task"""
        scheduled_time = datetime.utcnow() + timedelta(hours=1)
        payload = {"data": "test"}
        
        task = task_queue.enqueue(
            "process",
            payload,
            scheduled_at=scheduled_time
        )
        
        assert task.scheduled_at is not None
        assert mock_redis.zadd.called
    
    def test_dequeue_task(self, task_queue, mock_redis):
        """Test dequeueing a task"""
        task_id = "task-123"
        task_data = json.dumps({
            'task_id': task_id,
            'task_type': 'process',
            'payload': {'data': 'test'},
            'priority': 'NORMAL',
            'status': 'pending'
        })
        
        mock_redis.rpop.return_value = task_id.encode()
        mock_redis.hget.return_value = task_data.encode()
        
        task = task_queue.dequeue()
        
        assert task is not None
        assert task.task_id == task_id
        assert task.status == TaskStatus.PROCESSING
    
    def test_complete_task(self, task_queue, mock_redis):
        """Test completing a task"""
        task_id = "task-123"
        task_data = json.dumps({
            'task_id': task_id,
            'task_type': 'process',
            'payload': {'data': 'test'},
            'priority': 'NORMAL',
            'status': 'processing'
        })
        
        mock_redis.hget.return_value = task_data.encode()
        
        task_queue.complete(task_id)
        
        assert mock_redis.hset.called
        assert mock_redis.lrem.called
    
    def test_fail_task_with_retries(self, task_queue, mock_redis):
        """Test failing a task with retries"""
        task_id = "task-123"
        task_data = json.dumps({
            'task_id': task_id,
            'task_type': 'process',
            'payload': {'data': 'test'},
            'priority': 'NORMAL',
            'status': 'processing',
            'retry_count': 0,
            'max_retries': 3
        })
        
        mock_redis.hget.return_value = task_data.encode()
        
        task_queue.fail(task_id, "Test error")
        
        # Should retry since retry_count < max_retries
        assert mock_redis.zadd.called
        call_args = mock_redis.hset.call_args
        updated_task = json.loads(call_args[0][2])
        assert updated_task['status'] == 'retrying'
        assert updated_task['retry_count'] == 1
    
    def test_fail_task_to_dlq(self, task_queue, mock_redis):
        """Test moving task to dead letter queue"""
        task_id = "task-123"
        task_data = json.dumps({
            'task_id': task_id,
            'task_type': 'process',
            'payload': {'data': 'test'},
            'priority': 'NORMAL',
            'status': 'processing',
            'retry_count': 3,
            'max_retries': 3
        })
        
        mock_redis.hget.return_value = task_data.encode()
        
        task_queue.fail(task_id, "Permanent failure")
        
        # Should move to DLQ since retries exhausted
        assert mock_redis.lpush.called
        call_args = mock_redis.hset.call_args
        updated_task = json.loads(call_args[0][2])
        assert updated_task['status'] == 'dead_lettered'
    
    def test_get_queue_size(self, task_queue, mock_redis):
        """Test getting queue size"""
        mock_redis.llen.return_value = 5
        
        size = task_queue.get_queue_size()
        
        assert size == 20  # 4 priority queues * 5
    
    def test_get_queue_size_by_priority(self, task_queue, mock_redis):
        """Test getting queue size by priority"""
        mock_redis.llen.return_value = 10
        
        size = task_queue.get_queue_size(TaskPriority.CRITICAL)
        
        assert size == 10
    
    def test_get_dead_letter_tasks(self, task_queue, mock_redis):
        """Test retrieving dead letter queue tasks"""
        task_id = "task-123"
        task_data = json.dumps({
            'task_id': task_id,
            'task_type': 'process',
            'payload': {'data': 'test'},
            'priority': 'NORMAL',
            'status': 'dead_lettered'
        })
        
        mock_redis.lrange.return_value = [task_id.encode()]
        mock_redis.hget.return_value = task_data.encode()
        
        tasks = task_queue.get_dead_letter_tasks()
        
        assert len(tasks) == 1
        assert tasks[0].status == TaskStatus.DEAD_LETTERED
    
    def test_get_stats(self, task_queue, mock_redis):
        """Test getting queue statistics"""
        mock_redis.llen.return_value = 5
        mock_redis.hlen.return_value = 100
        
        stats = task_queue.get_stats()
        
        assert stats['queue_name'] == 'test'
        assert 'total_queued' in stats
        assert 'processing' in stats
        assert 'dead_lettered' in stats
        assert stats['total_tasks'] == 100


class TestTaskPriority:
    """Test TaskPriority enum"""
    
    def test_priority_ordering(self):
        """Test priority levels are ordered correctly"""
        assert TaskPriority.CRITICAL.value == 1
        assert TaskPriority.HIGH.value == 2
        assert TaskPriority.NORMAL.value == 3
        assert TaskPriority.LOW.value == 4
