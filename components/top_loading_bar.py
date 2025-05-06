"""
Top loading bar component for showing background activity.
"""
from dash import html

def create_top_loading_bar(visible=False):
    """
    Create a top loading bar component for indicating background activity.
    
    Args:
        visible: Whether the loading bar should be initially visible
        
    Returns:
        dash component: A html.Div component for the top loading bar
    """
    style = {"display": "block"} if visible else {"display": "none"}
    
    return html.Div(
        id="top-loading-bar",
        className="top-loading-bar",
        style=style
    )