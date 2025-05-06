from dash import html, dcc
import dash_bootstrap_components as dbc
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

def create_status_card():
    """
    Create a status card displaying system information and processing progress.
    
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
            html.H4("System Status", className="card-title"),
        ]),
        dbc.CardBody([
            html.Div([
                html.P("API Connection:", className="fw-bold"),
                html.P(
                    "Connected to HCHB FHIR API" if connected else "Not connected to API", 
                    id="api-status", 
                    className="text-success" if connected else "text-danger"
                ),
                html.Hr(),
                html.P("API Endpoint:", className="fw-bold"),
                html.P(api_base_url, className="text-primary"),
                html.Hr(),
                html.P("Last Data Refresh:", className="fw-bold"),
                html.Div(id="last-refresh"),
                html.Hr(),
                # Add Progress Tracking Section
                html.P("Current Process:", className="fw-bold"),
                html.Div(id="current-process", children="None"),
                html.Hr(),
                html.P("Processing Progress:", className="fw-bold"),
                dbc.Progress(id="progress-bar", value=0, style={"height": "20px"}, className="mb-2"),
                html.P(id="progress-text", children="No active process"),
                html.Hr(),
                html.P("Environment:", className="fw-bold"),
                html.P(environment, className="text-primary"),
                html.Hr(),
                html.P("Output Directory:", className="fw-bold"),
                html.P(os.getenv("OUTPUT_DIRECTORY", "output"), className="text-primary"),
            ]),
        ]),
    ], className="h-100 shadow")

def create_script_card(title, description, script_id, script_path, api_details=None):
    """
    Create a script card for running automation scripts.
    
    Args:
        title: Title of the script card
        description: Description of the script
        script_id: Unique ID for the script
        script_path: Path to the script module
        api_details: List of API details for the modal
        
    Returns:
        dash component: A dbc.Card component
    """
    # Create the script card
    return dbc.Card([
        dbc.CardHeader([
            html.H4(title, className="card-title"),
        ]),
        dbc.CardBody([
            html.P(description, className="card-text"),
            dbc.Button("Run Script", id=f"run-{script_id}", color="primary", className="mt-2"),
            html.Div(id=f"output-{script_id}", className="mt-3 text-muted"),
        ]),
        dbc.CardFooter([
            dbc.Button(
                "View API Details", 
                id=f"open-modal-{script_id}", 
                color="link", 
                className="text-decoration-none p-0"
            ),
            dbc.Modal([
                dbc.ModalHeader(f"{title} - API Details"),
                dbc.ModalBody([
                    html.P(detail) for detail in (api_details or [])
                ]),
                dbc.ModalFooter(
                    dbc.Button("Close", id=f"close-modal-{script_id}", className="ms-auto")
                ),
            ], id=f"modal-{script_id}", is_open=False),
        ]),
    ], className="h-100 shadow")