from dash import html, dcc
import dash_bootstrap_components as dbc
import os
import json
from datetime import datetime

def create_status_card():
    """
    Create a modern status card displaying system information and processing progress.
    
    Returns:
        dash component: A dbc.Card component
    """
    # Get environment information
    environment = os.getenv("ENV", "Production")
    api_base_url = os.getenv("API_BASE_URL", "https://api.hchb.com/fhir/r4")
    
    # Check if connection details are available
    connected = all([
        os.getenv("CLIENT_ID"),
        os.getenv("RESOURCE_SECURITY_ID"),
        os.getenv("AGENCY_SECRET"),
        os.getenv("TOKEN_URL")
    ])
    
    # Create status card
    return dbc.Card([
        dbc.CardHeader([
            html.H4([
                html.I(className="fas fa-server me-2"),
                "System Status"
            ], className="card-title d-flex align-items-center"),
        ]),
        dbc.CardBody([
            html.Div([
                dbc.Row([
                    dbc.Col(html.P("API Connection:", className="fw-bold"), width="auto"),
                    dbc.Col(
                        html.P([
                            html.I(className="fas fa-circle me-2 fa-xs"),
                            "Connected to HCHB FHIR API" if connected else "Not connected to API"
                        ], id="api-status", className="d-flex align-items-center text-success" if connected else "d-flex align-items-center text-danger")
                    )
                ], className="mb-3"),
                html.Hr(className="my-3"),
                
                dbc.Row([
                    dbc.Col(html.P("API Endpoint:", className="fw-bold"), width="auto"),
                    dbc.Col(html.P(api_base_url, className="text-primary"))
                ], className="mb-3"),
                html.Hr(className="my-3"),
                
                dbc.Row([
                    dbc.Col(html.P("Last Data Refresh:", className="fw-bold"), width="auto"),
                    dbc.Col(html.Div(id="last-refresh"))
                ], className="mb-3"),
                html.Hr(className="my-3"),
                
                # Add Progress Tracking Section
                dbc.Row([
                    dbc.Col(html.P("Current Process:", className="fw-bold"), width="auto"),
                    dbc.Col(html.Div(id="current-process", children="None", className="fw-bold text-primary"))
                ], className="mb-3"),
                html.Hr(className="my-3"),
                
                dbc.Row([
                    dbc.Col(html.P("Processing Progress:", className="fw-bold"), width="auto"),
                    dbc.Col([
                        dbc.Progress(
                            id="progress-bar", 
                            value=0, 
                            label="0%",
                            style={"height": "12px"}, 
                            className="mb-2"
                        ),
                        html.P(id="progress-text", children="No active process", className="text-muted fs-6")
                    ], width=12)
                ], className="mb-3"),
                html.Hr(className="my-3"),
                
                dbc.Row([
                    dbc.Col(html.P("Environment:", className="fw-bold"), width="auto"),
                    dbc.Col(html.P([
                        html.I(className="fas fa-cog me-2"),
                        environment
                    ], className="text-primary d-flex align-items-center"))
                ], className="mb-3"),
                html.Hr(className="my-3"),
                
                dbc.Row([
                    dbc.Col(html.P("Output Directory:", className="fw-bold"), width="auto"),
                    dbc.Col(html.P([
                        html.I(className="fas fa-folder-open me-2"),
                        os.getenv("OUTPUT_DIRECTORY", "output")
                    ], className="text-primary d-flex align-items-center"))
                ], className="mb-3"),
            ]),
        ]),
    ], className="h-100 shadow")

def create_script_card(title, description, script_id, script_path, api_details=None):
    """
    Create a modern script card for running automation scripts with enhanced log display.
    
    Args:
        title: Title of the script card
        description: Description of the script
        script_id: Unique ID for the script
        script_path: Path to the script module
        api_details: List of API details for the modal
        
    Returns:
        dash component: A dbc.Card component
    """
    # Define icon based on script ID
    icons = {
        "alert-media": "fas fa-bell",
        "coordination-notes": "fas fa-clipboard",
        "patients": "fas fa-user",
        "weekly-appointments": "fas fa-calendar-alt",
        "workers": "fas fa-users"
    }
    
    icon_class = icons.get(script_id, "fas fa-cogs")
    
    # Create the script card
    return dbc.Card([
        dbc.CardHeader([
            html.H4([
                html.I(className=f"{icon_class} me-2"),
                title
            ], className="card-title d-flex align-items-center"),
        ]),
        dbc.CardBody([
            html.P(description, className="card-text mb-4"),
            dbc.Row([
                dbc.Col([
                    dbc.Button([
                        html.I(className="fas fa-play me-2"),
                        "Run Script"
                    ], id={"type": "run-script", "index": script_id}, color="primary", className="me-2"),
                ], width="auto"),
                dbc.Col([
                    dbc.Button([
                        html.I(className="fas fa-info-circle me-2"),
                        "API Details"
                    ], id={"type": "open-modal", "index": script_id}, color="secondary"),
                ], width="auto"),
            ], className="mb-4"),
            
            # Log container (initially hidden)
            html.Div([
                html.Hr(className="my-3"),
                html.H5([
                    html.I(className="fas fa-terminal me-2"),
                    "Execution Log:"
                ], className="mb-3 d-flex align-items-center"),
                dbc.Spinner(
                    html.Div(
                        id={"type": "script-output", "index": script_id}, 
                        className="log-output",
                        style={"maxHeight": "250px", "overflowY": "auto"}
                    ),
                    color="primary",
                    size="sm",
                    spinner_style={"position": "absolute", "top": "50%", "left": "50%"}
                )
            ], id={"type": "log-container", "index": script_id}, className="log-container", style={"display": "none"}),
        ]),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle([
                html.I(className=f"{icon_class} me-2"),
                f"{title} - API Details"
            ])),
            dbc.ModalBody([
                html.Div([
                    html.P(api_details[0], className="lead mb-4") if api_details and len(api_details) > 0 else None,
                    *[
                        html.P(detail, className="mb-3") 
                        if not detail.startswith("•") else 
                        html.Div([
                            html.I(className="fas fa-check-circle me-2 text-primary"),
                            detail[1:].strip()
                        ], className="mb-2 d-flex align-items-center")
                        for detail in (api_details[1:] if api_details and len(api_details) > 1 else [])
                    ]
                ])
            ]),
            dbc.ModalFooter(
                dbc.Button([
                    html.I(className="fas fa-times me-2"),
                    "Close"
                ], id={"type": "close-modal", "index": script_id}, className="ms-auto")
            ),
        ], id={"type": "modal", "index": script_id}, is_open=False, size="lg", scrollable=True),
    ], className="h-100 shadow")