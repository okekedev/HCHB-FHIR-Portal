"""
Progress tracking utility for Healing Hands automation scripts.
Tracks and updates progress for long-running processes.
"""
import os
import json
from datetime import datetime

class ProgressTracker:
    """
    Tracks and updates progress for long-running processes.
    Provides a way for the UI to check progress status.
    """
    def __init__(self, process_name, total_items=0):
        """
        Initialize the progress tracker.
        
        Args:
            process_name: Name of the process being tracked
            total_items: Total number of items to process
        """
        self.process_name = process_name
        self.total_items = total_items
        self.processed_items = 0
        self.status = "running"  # running, completed, error
        self.message = f"Processing {process_name}"
        self.start_time = datetime.now()
        self.end_time = None
        self.error = None
        
        # Create progress file directory if it doesn't exist
        self.progress_dir = os.path.join("output", ".progress")
        os.makedirs(self.progress_dir, exist_ok=True)
        
        # Initialize progress file
        self._update_progress_file()
    
    def update(self, processed_items, message=None):
        """
        Update progress status.
        
        Args:
            processed_items: Number of items processed so far
            message: Optional status message
        """
        self.processed_items = processed_items
        if message:
            self.message = message
        self._update_progress_file()
    
    def increment(self, count=1, message=None):
        """
        Increment the processed items count.
        
        Args:
            count: Number of items to add to the count
            message: Optional status message
        """
        self.processed_items += count
        if message:
            self.message = message
        self._update_progress_file()
    
    def complete(self, message="Process completed successfully"):
        """
        Mark the process as completed.
        
        Args:
            message: Completion message
        """
        self.status = "completed"
        self.message = message
        self.end_time = datetime.now()
        self._update_progress_file()
    
    def set_error(self, error_message):
        """
        Mark the process as failed with an error.
        
        Args:
            error_message: Error message
        """
        self.status = "error"
        self.message = f"Error: {error_message}"
        self.error = error_message
        self.end_time = datetime.now()
        self._update_progress_file()
    
    def _update_progress_file(self):
        """Update the progress file with current status"""
        progress_data = {
            "process_name": self.process_name,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "percentage": round((self.processed_items / self.total_items) * 100) if self.total_items > 0 else 0,
            "status": self.status,
            "message": self.message,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": str(datetime.now() - self.start_time) if self.start_time else None,
            "error": self.error
        }
        
        # Write to process-specific file
        filename = f"{self.process_name.replace(' ', '_').lower()}.json"
        filepath = os.path.join(self.progress_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(progress_data, f)
        
        # Also update current.json to indicate the latest process
        current_filepath = os.path.join(self.progress_dir, 'current.json')
        with open(current_filepath, 'w') as f:
            json.dump({"current_process": self.process_name, "updated_at": datetime.now().isoformat()}, f)

def get_current_progress():
    """
    Get the progress of the currently running process.
    
    Returns:
        Dictionary with progress information or None if no process is running
    """
    progress_dir = os.path.join("output", ".progress")
    current_filepath = os.path.join(progress_dir, 'current.json')
    
    if not os.path.exists(current_filepath):
        return None
    
    try:
        # Read current process info
        with open(current_filepath, 'r') as f:
            current_info = json.load(f)
        
        # Check if it was updated recently (within 5 minutes)
        updated_at = datetime.fromisoformat(current_info["updated_at"])
        if (datetime.now() - updated_at).total_seconds() > 300:
            # Process likely stopped without updating status
            return None
        
        # Get detailed progress for the current process
        process_name = current_info["current_process"]
        filename = f"{process_name.replace(' ', '_').lower()}.json"
        filepath = os.path.join(progress_dir, filename)
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r') as f:
            return json.load(f)
            
    except Exception as e:
        print(f"Error getting progress: {e}")
        return None