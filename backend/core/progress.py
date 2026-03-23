from typing import Dict, List, Optional
from loguru import logger as log

def calculate_parallel_progress(tasks_progress: Dict[str, float]) -> float:
    """
    Calculates the weighted average of progress for multiple parallel tasks.
    
    Args:
        tasks_progress: A dictionary mapping task IDs (or labels) to their current progress (0-100).
        
    Returns:
        The overall progress as a float from 0 to 100.
    """
    if not tasks_progress:
        return 0.0
    
    total = sum(tasks_progress.values())
    count = len(tasks_progress)
    
    progress = total / count
    return round(min(progress, 100.0), 2)

async def update_video_progress(video, task_id: str, progress: float, repository=None, expected_tasks: Optional[List[str]] = None):
    """
    Updates the rendering_progress of a video model based on individual task updates.
    
    Args:
        video: The VideoModel instance.
        task_id: Unique identifier for the sub-task (e.g., aspect ratio).
        progress: Progress of this specific task (0-100).
        repository: Optional VideoRepository to persist changes.
        expected_tasks: Optional list of task IDs to initialize to 0.0 if not yet present.
    """
    # Sprint 250: Use the official parallel_tasks dict from model
    parallel_tasks = getattr(video, 'parallel_tasks', None)
    if parallel_tasks is None:
        parallel_tasks = {}
        video.parallel_tasks = parallel_tasks

    # Initialize expected tasks if provided and not already in progress
    if expected_tasks:
        for tid in expected_tasks:
            if tid not in parallel_tasks:
                parallel_tasks[tid] = 0.0

    parallel_tasks[task_id] = progress
    
    new_total_progress = calculate_parallel_progress(parallel_tasks)
    
    # Updated to NOT save here anymore. 
    # Caller is responsible for persistence (e.g. via _save_video_merged)
    # this avoids clobbering final states with intermediate progress states.
    current_progress = getattr(video, 'rendering_progress', 0.0) or 0.0
    if new_total_progress > current_progress:
        video.rendering_progress = new_total_progress
        video.progress = new_total_progress # Also sync main progress
    
    return new_total_progress
