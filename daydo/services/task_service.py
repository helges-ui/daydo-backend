"""
Task service for DayDo application.
Handles task-related business logic including star count management.
"""
from typing import Optional
from ..models import User, Task


class TaskService:
    """Service for task operations"""
    
    @staticmethod
    def adjust_star_count(user: User, delta: int) -> None:
        """
        Increment or decrement the child's star count, ensuring it never goes below zero.
        
        Args:
            user: User instance (should be a child user)
            delta: Change in star count (positive to add, negative to subtract)
        """
        if not user or delta == 0:
            return

        # Only adjust for child accounts
        is_child = False
        if hasattr(user, 'is_child_user'):
            is_child = user.is_child_user
        role_value = getattr(user, 'role', None)
        if role_value == 'CHILD_USER':
            is_child = True

        if not is_child:
            return

        current = getattr(user, 'star_count', 0) or 0
        new_value = current + delta
        if new_value < 0:
            new_value = 0

        if new_value != current:
            user.star_count = new_value
            user.save(update_fields=['star_count', 'updated_at'])
    
    @staticmethod
    def toggle_task_completion(task: Task) -> Task:
        """
        Toggle task completion status and adjust star count accordingly.
        
        Args:
            task: Task instance to toggle
            
        Returns:
            Task: Updated task instance
        """
        if task.completed:
            task.mark_incomplete()
            TaskService.adjust_star_count(task.assigned_to, -1)
        else:
            task.mark_completed()
            TaskService.adjust_star_count(task.assigned_to, 1)
        
        return task

