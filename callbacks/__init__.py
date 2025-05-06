"""
Callbacks package initialization.
Import and register all callbacks for the Healing Hands Data Automation dashboard.
"""

def register_all_callbacks(app):
    """
    Register all callbacks with the app.
    
    Args:
        app: The Dash app instance
    """
    # Import all callback modules
    from callbacks.modal_callbacks import register_modal_callbacks
    from callbacks.script_callbacks import register_script_callbacks
    from callbacks.status_callbacks import register_status_callbacks
    from callbacks.loading_callbacks import register_loading_callbacks
    
    # Register each set of callbacks
    register_modal_callbacks(app)
    register_script_callbacks(app)
    register_status_callbacks(app)
    register_loading_callbacks(app)
    
    print("All callbacks registered successfully")