"""
Modal dialog callbacks for the Healing Hands Data Automation dashboard.
"""
import dash
from dash import callback, Input, Output, State, ALL, MATCH

def register_modal_callbacks(app):
    """
    Register all modal-related callbacks with the app.
    
    Args:
        app: The Dash app instance
    """
    @app.callback(
        Output({"type": "modal", "index": MATCH}, "is_open"),
        [Input({"type": "open-modal", "index": MATCH}, "n_clicks"),
         Input({"type": "close-modal", "index": MATCH}, "n_clicks")],
        [State({"type": "modal", "index": MATCH}, "is_open")],
        prevent_initial_call=True
    )
    def toggle_modal(open_clicks, close_clicks, is_open):
        """
        Toggle the visibility of a modal dialog.
        
        Args:
            open_clicks: Number of clicks on the open button
            close_clicks: Number of clicks on the close button
            is_open: Current state of the modal
            
        Returns:
            New state for the modal
        """
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
            
        prop_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if "open-modal" in prop_id:
            return True
        elif "close-modal" in prop_id:
            return False
            
        return is_open