"""
Loading indicator callbacks for the Healing Hands Data Automation dashboard.
"""
import dash
from dash import callback, Input, Output, State, ALL, MATCH, ctx

def register_loading_callbacks(app):
    """
    Register loading indicator callbacks with the app.
    
    Args:
        app: The Dash app instance
    """
    # Callback to show/hide loading indicators when script is running
    @app.callback(
        [Output({"type": "loading-overlay", "index": MATCH}, "style"),
         Output({"type": "status-badge", "index": MATCH}, "style")],
        Input({"type": "run-script", "index": MATCH}, "n_clicks"),
        [State({"type": "run-script", "index": MATCH}, "id")],
        prevent_initial_call=True
    )
    def toggle_loading_indicators(n_clicks, button_id):
        """
        Show loading indicators when a script is run and hide them when complete.
        
        Args:
            n_clicks: Number of clicks on the run button
            button_id: ID of the button that was clicked
            
        Returns:
            Tuple of (overlay_style, badge_style)
        """
        if not ctx.triggered:
            return dash.no_update, dash.no_update
        
        # Show loading indicators when button is clicked
        if n_clicks:
            # Show loading overlay and badge
            return {"display": "flex"}, {"display": "inline-flex"}
        
        return dash.no_update, dash.no_update
    
    # Callback to hide loading indicators when script execution completes
    @app.callback(
        [Output({"type": "loading-overlay", "index": MATCH}, "style", allow_duplicate=True),
         Output({"type": "status-badge", "index": MATCH}, "style", allow_duplicate=True),
         Output({"type": "status-badge", "index": MATCH}, "children")],
        Input({"type": "script-status", "index": MATCH}, "children"),
        [State({"type": "run-script", "index": MATCH}, "id")],
        prevent_initial_call=True
    )
    def update_indicators_on_completion(status_text, button_id):
        """
        Update loading indicators when script execution completes.
        
        Args:
            status_text: Status text from script execution
            button_id: ID of the run button
            
        Returns:
            Tuple of (overlay_style, badge_style, badge_text)
        """
        if not status_text:
            return dash.no_update, dash.no_update, dash.no_update
        
        # Hide loading overlay
        overlay_style = {"display": "none"}
        
        # Update badge to show completion status
        if "successfully" in str(status_text):
            # Success badge
            badge_style = {"display": "inline-flex"}
            badge_text = [
                html.Div(className="success-icon me-2"),
                html.Span("Completed")
            ]
        elif "Error" in str(status_text) or "failed" in str(status_text):
            # Error badge
            badge_style = {"display": "inline-flex"}
            badge_text = [
                html.Div(className="error-icon me-2"),
                html.Span("Failed")
            ]
        else:
            # Hide badge if status is ambiguous
            badge_style = {"display": "none"}
            badge_text = dash.no_update
        
        return overlay_style, badge_style, badge_text
    
    # Callback to show the API operations active indicator when any script is running
    @app.callback(
        Output("api-active-indicator", "style"),
        [Input({"type": "loading-overlay", "index": ALL}, "style")],
        prevent_initial_call=True
    )
    def update_api_activity_indicator(loading_styles):
        """
        Show the API operations active indicator when any script is running.
        
        Args:
            loading_styles: List of style dictionaries for all loading overlays
            
        Returns:
            Style dictionary for the API activity indicator
        """
        # Check if any loading overlay is visible
        any_loading = any(
            style.get("display") == "flex" 
            for style in loading_styles 
            if style is not None
        )
        
        if any_loading:
            return {"display": "flex"}
        else:
            return {"display": "none"}