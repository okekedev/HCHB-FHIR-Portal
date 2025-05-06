"""
Status update callbacks for the Healing Hands Data Automation dashboard.
"""
import dash
from dash import callback, Input, Output, html
import time
from datetime import datetime
import os
import json
from utils.progress_tracker import get_current_progress

def register_status_callbacks(app):
    """
    Register status update callbacks with the app.
    
    Args:
        app: The Dash app instance
    """
    # Callback for Last Refresh in Status Card
    @app.callback(
        Output("last-refresh", "children"),
        Input("status-interval", "n_intervals"),
    )
    def update_last_refresh(n_intervals):
        """
        Update the last refresh timestamp.
        
        Args:
            n_intervals: Number of interval refreshes
            
        Returns:
            HTML component with refresh timestamp
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        return html.P([
            html.I(className="fas fa-sync-alt me-2"),
            f"Last Updated: {timestamp}"
        ], className="text-info")

    # Callback for updating progress information
    @app.callback(
        [Output("current-process", "children"),
         Output("progress-bar", "value"),
         Output("progress-bar", "label"),
         Output("progress-bar", "color"),
         Output("progress-text", "children")],
        Input("status-interval", "n_intervals"),
    )
    def update_progress(n_intervals):
        """
        Update the progress indicators based on current progress.
        
        Args:
            n_intervals: Number of interval refreshes
            
        Returns:
            Tuple of (process_name, progress_value, progress_label, progress_color, progress_text)
        """
        # Get current progress
        progress = get_current_progress()
        
        if not progress:
            return [
                html.Span([
                    html.I(className="fas fa-hourglass me-2"),
                    "No Active Process"
                ]), 
                0, 
                "", 
                "primary",
                "No active process running"
            ]
        
        # Format process name
        process_name = progress["process_name"]
        
        # Calculate percentage
        percentage = progress["percentage"]
        
        # Determine progress bar color based on status
        if progress["status"] == "completed":
            color = "success"
            icon = "fas fa-check-circle"
        elif progress["status"] == "error":
            color = "danger"
            icon = "fas fa-exclamation-circle"
        else:
            color = "primary"
            icon = "fas fa-sync fa-spin"
        
        # Format progress text
        if progress["status"] == "running":
            progress_text = f"{progress['message']} - {progress['processed_items']} of {progress['total_items']} items ({percentage}% complete)"
        elif progress["status"] == "completed":
            progress_text = f"{progress['message']} in {progress['duration']}"
        elif progress["status"] == "error":
            progress_text = f"Error: {progress['error']}"
        else:
            progress_text = progress["message"]
        
        # Return updated values
        return [
            html.Span([
                html.I(className=f"{icon} me-2"),
                f"{process_name}"
            ], className="d-flex align-items-center"),
            percentage, 
            f"{percentage}%" if percentage > 0 else "", 
            color,
            progress_text
        ]
    
    # Callback to update active processes list
    @app.callback(
        Output("active-processes-list", "children"),
        Input("status-interval", "n_intervals"),
    )
    def update_active_processes_list(n_intervals):
        """
        Update the list of active processes.
        
        Args:
            n_intervals: Number of interval refreshes
            
        Returns:
            List of active process components
        """
        # Get progress directory
        progress_dir = os.path.join("output", ".progress")
        if not os.path.exists(progress_dir):
            return html.P("No active processes", className="text-muted")
        
        # Check all JSON files except current.json
        process_files = [f for f in os.listdir(progress_dir) 
                        if f.endswith('.json') and f != 'current.json']
        
        active_processes = []
        for file in process_files:
            try:
                with open(os.path.join(progress_dir, file), 'r') as f:
                    process_data = json.load(f)
                    
                # Only include recent active processes (last 5 minutes)
                if process_data.get("status") == "running":
                    # Check if recently updated
                    if "start_time" in process_data:
                        try:
                            start_time = datetime.fromisoformat(process_data["start_time"])
                            if (datetime.now() - start_time).total_seconds() < 300:
                                active_processes.append(process_data)
                        except (ValueError, TypeError):
                            # Skip if time parsing fails
                            continue
            except Exception:
                continue
        
        if not active_processes:
            return html.Div([
                html.P("No active processes", className="text-muted"),
                html.P([
                    html.I(className="fas fa-info-circle me-2"),
                    "Run an automation tool to see process status here"
                ], className="text-primary small mt-3")
            ], className="text-center p-4")
        
        # Create list of active processes with enhanced UI
        import dash_bootstrap_components as dbc
        
        process_list = []
        
        # Sort processes by percentage completed (descending)
        active_processes.sort(key=lambda x: x.get("percentage", 0), reverse=True)
        
        # Add cascade effect with different animation delays
        for i, process in enumerate(active_processes):
            # Calculate animation delay class (limit to 5 items)
            delay_class = f"fade-in-cascade-{min(i+1, 5)}"
            
            # Calculate process percentage
            percentage = process.get("percentage", 0)
            
            # Create process card with animation
            process_card = dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Div(className="processing-spinner"),
                        html.Span(process.get("process_name", "Unknown Process"), 
                                className="fw-bold ms-2")
                    ], className="d-flex align-items-center mb-3"),
                    
                    html.P(process.get("message", "Processing..."), 
                          className="text-muted small mb-3"),
                    
                    dbc.Progress(
                        value=percentage,
                        label=f"{percentage}%" if percentage > 20 else "",
                        className="mb-2 animated-progress",
                        style={"height": "8px"}
                    ),
                    
                    html.Div([
                        html.Span(f"{process.get('processed_items', 0)} of {process.get('total_items', 0)} items", 
                                className="small text-primary"),
                        html.Span(f"Started: {_format_time(process.get('start_time', ''))}", 
                                className="small text-muted ms-auto")
                    ], className="d-flex justify-content-between mt-2")
                ], className="p-3")
            ], className=f"mb-3 shadow-sm active-process-card fade-in {delay_class}")
            
            process_list.append(process_card)
        
        return html.Div(process_list)

def _format_time(timestamp_str):
    """Format a timestamp string to a readable format."""
    if not timestamp_str:
        return "Unknown"
    
    try:
        # Parse ISO format timestamp
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        
        # Format as readable time
        return dt.strftime("%H:%M:%S")
    except (ValueError, TypeError):
        return "Unknown"