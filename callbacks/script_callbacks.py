"""
Script execution callbacks for the Healing Hands Data Automation dashboard.
"""
import dash
from dash import callback, Input, Output, State, ALL, MATCH, ctx
from utils.script_runner import run_script_with_output

def register_script_callbacks(app):
    """
    Register script execution callbacks with the app.
    
    Args:
        app: The Dash app instance
    """
    # Callback to show/hide log container when script is run
    @app.callback(
        Output({"type": "log-container", "index": MATCH}, "style"),
        Input({"type": "run-script", "index": MATCH}, "n_clicks"),
        prevent_initial_call=True
    )
    def toggle_log_container(n_clicks):
        """
        Show log container when script is run.
        
        Args:
            n_clicks: Number of clicks on the run button
            
        Returns:
            Style dict for the log container
        """
        if n_clicks:
            return {"display": "block"}
        return dash.no_update
    
    # Callback for script execution and results with loading states
    @app.callback(
        [Output({"type": "script-output", "index": MATCH}, "children"),
         Output({"type": "script-status", "index": MATCH}, "children"),
         Output({"type": "script-status", "index": MATCH}, "style"),
         Output({"type": "script-status", "index": MATCH}, "className")],
        Input({"type": "run-script", "index": MATCH}, "n_clicks"),
        State({"type": "run-script", "index": MATCH}, "id"),
        prevent_initial_call=True
    )
    def run_script_callback(n_clicks, button_id):
        """
        Run a script and update the output and status.
        
        Args:
            n_clicks: Number of clicks on the run button
            button_id: ID of the button that was clicked
            
        Returns:
            Tuple of (output_text, status_text, status_style, status_class)
        """
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Get script ID from button
        script_id = button_id["index"]
        
        # Get script information based on script_id
        script_paths = {
            "alert-media": "scripts.alert_media_batch",
            "coordination-notes": "scripts.coordination_notes_csv",
            "patients": "scripts.patients_csv",
            "weekly-appointments": "scripts.weekly_appointments_csv",
            "workers": "scripts.workers_csv"
        }
        
        script_path = script_paths.get(script_id)
        if not script_path:
            return "Invalid script path", "Error: Invalid script path", {"display": "block"}, "alert alert-danger"
        
        # Run the script
        status, output = run_script_with_output(script_path)
        
        # Set status information based on result
        if status == "SUCCESS":
            status_text = "✅ Script executed successfully!"
            status_style = {"display": "block"}
            status_class = "alert alert-success"
        else:
            status_text = "❌ Script execution failed. See log for details."
            status_style = {"display": "block"}
            status_class = "alert alert-danger"
        
        return output, status_text, status_style, status_class
    
    # Map of script IDs to their readable names
    script_names = {
        "alert-media": "Alert Media Integration",
        "coordination-notes": "Coordination Notes",
        "patients": "Patient Demographics",
        "weekly-appointments": "Weekly Appointments",
        "workers": "Workers Directory"
    }
    
    # Add callback to update process tracking store when script runs
    @app.callback(
        Output("process-status", "data"),
        [Input({"type": "run-script", "index": ALL}, "n_clicks")],
        [State({"type": "run-script", "index": ALL}, "id"),
         State("process-status", "data")],
        prevent_initial_call=True
    )
    def update_process_status(n_clicks_list, button_ids, current_status):
        """
        Update the process status store when a script runs.
        
        Args:
            n_clicks_list: List of click counts for all run buttons
            button_ids: List of button IDs
            current_status: Current process status data
            
        Returns:
            Updated process status data
        """
        if not ctx.triggered:
            return dash.no_update
            
        # Get the triggered input
        triggered_id = ctx.triggered_id
        if not triggered_id or "index" not in triggered_id:
            return dash.no_update
            
        # Get the script ID
        script_id = triggered_id["index"]
        script_name = script_names.get(script_id, script_id)
        
        # Update process status
        if current_status is None:
            current_status = {}
            
        current_status[script_id] = {
            "name": script_name,
            "status": "running",
            "start_time": dash.no_update  # Use actual timestamp in status_callbacks.py
        }
        
        return current_status