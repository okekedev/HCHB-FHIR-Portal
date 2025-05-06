import dash
from dash import dcc, html, callback, Input, Output, State, ALL, MATCH
import dash_bootstrap_components as dbc
import time
import json
from datetime import datetime
from dotenv import load_dotenv
import os

# Import components
from components.card import create_script_card
from components.status import create_status_card
from components.navbar import create_navbar

# Import utilities
from utils.script_runner import run_script_with_output
from utils.progress_tracker import get_current_progress

# Load environment variables
load_dotenv()

# Initialize the Dash app with Bootstrap theme and custom CSS
app = dash.Dash(
    __name__, 
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',  # Add Font Awesome icons
        'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Roboto+Mono&display=swap'  # Add modern fonts
    ],
    assets_folder="assets",
    suppress_callback_exceptions=True
)
app.title = "Healing Hands Data Automation"
server = app.server  # For deployment

# Dashboard layout
app.layout = html.Div([
    # Navigation bar at the top
    create_navbar(),
    
    # Main container
    dbc.Container([
        # Header with improved styling
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H1([
                        html.I(className="fas fa-heartbeat me-3 text-danger"),
                        "Healing Hands Data Automation"
                    ], className="display-4 text-center text-primary my-4 d-flex align-items-center justify-content-center"),
                    html.P("Streamline patient data collection and care coordination with intelligent automation", 
                           className="lead text-center text-muted mb-4"),
                    html.Hr(className="my-4"),
                ], className="text-center")
            ])
        ]),
        
        # Dashboard quick stats
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    html.Div([
                        html.I(className="fas fa-users fa-2x text-primary"),
                        html.H4("Patient Data", className="mt-3 mb-0"),
                        html.P("Demographics & Coordination", className="text-muted")
                    ], className="text-center p-4")
                ], className="shadow-sm border-0 rounded mb-4")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    html.Div([
                        html.I(className="fas fa-calendar-alt fa-2x text-primary"),
                        html.H4("Appointments", className="mt-3 mb-0"),
                        html.P("Weekly Scheduling & Visits", className="text-muted")
                    ], className="text-center p-4")
                ], className="shadow-sm border-0 rounded mb-4")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    html.Div([
                        html.I(className="fas fa-clipboard fa-2x text-primary"),
                        html.H4("Coordination", className="mt-3 mb-0"),
                        html.P("Notes & Documentation", className="text-muted")
                    ], className="text-center p-4")
                ], className="shadow-sm border-0 rounded mb-4")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    html.Div([
                        html.I(className="fas fa-bell fa-2x text-primary"),
                        html.H4("Alerts", className="mt-3 mb-0"),
                        html.P("Critical Notifications", className="text-muted")
                    ], className="text-center p-4")
                ], className="shadow-sm border-0 rounded mb-4")
            ], width=3),
        ]),
        
        # Main content - Script cards
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="fas fa-tasks me-2"),
                    "Automation Tools"
                ], className="mb-4 mt-2 d-flex align-items-center"),
            ], width=12),
        ]),
        
        # First row of script cards
        dbc.Row([
            # Alert Media Batch Script Card
            dbc.Col([
                create_script_card(
                    title="Alert Media Integration",
                    description="Run the Alert Media batch process to sync healthcare alerts with the notification system.",
                    script_id="alert-media",
                    script_path="scripts.alert_media_batch",
                    api_details=[
                        "This script extracts alert data from the HCHB FHIR API and prepares notifications for the Alert Media system.",
                        "It processes critical patient alerts that require immediate attention from healthcare providers.",
                        "API Endpoints Used:",
                        "• Patient API - To retrieve patient demographic information",
                        "• Care Team API - To identify assigned healthcare providers",
                        "• Condition API - To identify critical patient conditions",
                    ]
                )
            ], md=6, xl=4, className="mb-4"),
            
            # Coordination Notes Script Card
            dbc.Col([
                create_script_card(
                    title="Coordination Notes",
                    description="Run the Coordination Notes extraction process to retrieve all care coordination notes.",
                    script_id="coordination-notes",
                    script_path="scripts.coordination_notes_csv",
                    api_details=[
                        "This script retrieves coordination notes from the HCHB FHIR API, which contain important information about care coordination activities.",
                        "It processes interdisciplinary team communications and patient care planning notes.",
                        "API Endpoints Used:",
                        "• Document Reference - Coordination Note API - For retrieving care coordination documentation",
                        "• Episode of Care API - To link notes to specific care episodes",
                        "• Practitioner API - To identify note authors and recipients",
                    ]
                )
            ], md=6, xl=4, className="mb-4"),
            
            # Patients Script Card
            dbc.Col([
                create_script_card(
                    title="Patient Demographics",
                    description="Run the Patients data extraction process to retrieve comprehensive patient information.",
                    script_id="patients",
                    script_path="scripts.patients_csv",
                    api_details=[
                        "This script extracts comprehensive patient demographic and clinical information from the HCHB FHIR API.",
                        "It includes personal details, contact information, diagnoses, and care episodes.",
                        "API Endpoints Used:",
                        "• Patient API - To retrieve comprehensive patient demographic information",
                        "• Condition - Diagnoses API - To retrieve patient diagnoses",
                        "• Episode of Care API - To retrieve patient care episodes",
                        "• Related Person - Episode Contact API - To retrieve patient emergency contacts",
                        "• Living Arrangement API - To retrieve patient living situation",
                    ]
                )
            ], md=6, xl=4, className="mb-4"),
        ]),
        
        # Second row of script cards
        dbc.Row([
            # Weekly Appointments Script Card
            dbc.Col([
                create_script_card(
                    title="Weekly Appointments",
                    description="Run the Weekly Appointments extraction process to retrieve scheduled patient visits.",
                    script_id="weekly-appointments",
                    script_path="scripts.weekly_appointments_csv",
                    api_details=[
                        "This script extracts weekly appointment data from the HCHB FHIR API.",
                        "It includes scheduled visits, visit types, assigned caregivers, and visit details.",
                        "API Endpoints Used:",
                        "• Appointment - Patient Visit API - To retrieve scheduled patient visits",
                        "• Appointment - Schedule API - To retrieve visit schedules",
                        "• Care Team API - To identify assigned healthcare providers",
                        "• Service Location API - To retrieve visit locations",
                        "• Worker API - To retrieve caregiver information",
                    ]
                )
            ], md=6, className="mb-4"),
            
            # Workers Script Card
            dbc.Col([
                create_script_card(
                    title="Workers Directory",
                    description="Run the Workers data extraction process to retrieve information about all healthcare workers.",
                    script_id="workers",
                    script_path="scripts.workers_csv",
                    api_details=[
                        "This script extracts worker data from the HCHB FHIR API.",
                        "It includes healthcare professionals, their roles, qualifications, and assignments.",
                        "API Endpoints Used:",
                        "• Worker API - To retrieve healthcare worker information",
                        "• Worker Location API - To retrieve worker service areas",
                        "• Organization - Team API - To retrieve team assignments",
                        "• Organization - Branch API - To retrieve branch assignments",
                    ]
                )
            ], md=6, className="mb-4"),
        ]),
        
        # System Status Card in a separate row
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="fas fa-chart-line me-2"),
                    "System Status"
                ], className="mb-4 mt-2 d-flex align-items-center"),
            ], width=12),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4([
                            html.I(className="fas fa-server me-2"),
                            "System Overview"
                        ], className="card-title d-flex align-items-center"),
                    ]),
                    dbc.CardBody([
                        html.Div(id="last-refresh"),
                        html.Div(id="current-process", className="mt-3 fw-bold"),
                        dbc.Progress(id="progress-bar", value=0, className="my-3"),
                        html.P(id="progress-text", className="text-muted")
                    ])
                ], className="shadow h-100")
            ], md=12, xl=6, className="mb-4"),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4([
                            html.I(className="fas fa-cogs me-2"),
                            "Environment"
                        ], className="card-title d-flex align-items-center"),
                    ]),
                    dbc.CardBody([
                        html.P([
                            html.Span("API Status: ", className="fw-bold me-2"),
                            html.Span([
                                html.I(className="fas fa-check-circle text-success me-2"),
                                "Connected"
                            ], className="d-inline-flex align-items-center")
                        ]),
                        html.P([
                            html.Span("API URL: ", className="fw-bold me-2"),
                            html.Code(os.getenv('API_BASE_URL', 'https://api.hchb.com/fhir/r4'),
                                     className="bg-light rounded px-2 py-1")
                        ]),
                        html.P([
                            html.Span("Environment: ", className="fw-bold me-2"),
                            html.Span(os.getenv('ENV', 'Production'), className="text-primary")
                        ]),
                        html.P([
                            html.Span("Output Directory: ", className="fw-bold me-2"),
                            html.Code(os.getenv('OUTPUT_DIRECTORY', 'output'),
                                     className="bg-light rounded px-2 py-1")
                        ])
                    ])
                ], className="shadow h-100")
            ], md=12, xl=6, className="mb-4"),
        ]),
        
        # Footer
        html.Footer([
            html.Hr(className="my-4"),
            dbc.Row([
                dbc.Col([
                    html.P([
                        html.I(className="fas fa-heartbeat me-2 text-danger"),
                        "Healing Hands Data Automation Dashboard © 2025"
                    ], className="text-center text-muted mb-1"),
                    html.P([
                        "Powered by ",
                        html.A("HCHB FHIR API", href="#", className="text-decoration-none")
                    ], className="text-center text-muted small")
                ])
            ])
        ], className="mt-4"),
    ], fluid=True, className="p-4"),
    
    # Store for tracking active processes
    dcc.Store(id="process-status"),
    
    # Interval for updating status
    dcc.Interval(id="status-interval", interval=1000, n_intervals=0),
])

# Register callbacks for script modals
@app.callback(
    Output({"type": "modal", "index": MATCH}, "is_open"),
    [Input({"type": "open-modal", "index": MATCH}, "n_clicks"),
     Input({"type": "close-modal", "index": MATCH}, "n_clicks")],
    [State({"type": "modal", "index": MATCH}, "is_open")],
    prevent_initial_call=True
)
def toggle_modal(open_clicks, close_clicks, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    prop_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if "open-modal" in prop_id:
        return True
    elif "close-modal" in prop_id:
        return False
    return is_open

# Callback to show/hide log container when script is run
@app.callback(
    Output({"type": "log-container", "index": MATCH}, "style"),
    Input({"type": "run-script", "index": MATCH}, "n_clicks"),
    prevent_initial_call=True
)
def toggle_log_container(n_clicks):
    """Show log container when script is run"""
    if n_clicks:
        return {"display": "block"}
    return dash.no_update

# Callback for script execution
@app.callback(
    Output({"type": "script-output", "index": MATCH}, "children"),
    Input({"type": "run-script", "index": MATCH}, "n_clicks"),
    State({"type": "run-script", "index": MATCH}, "id"),
    prevent_initial_call=True
)
def run_script_callback(n_clicks, button_id):
    if not n_clicks:
        return dash.no_update
    
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
        return "Invalid script path"
    
    # Run the script
    status, output = run_script_with_output(script_path)
    
    # Format the output with colors
    colored_output = output
    if status == "SUCCESS":
        return colored_output
    else:
        return colored_output

# Callback for Last Refresh in Status Card
@app.callback(
    Output("last-refresh", "children"),
    Input("status-interval", "n_intervals"),
)
def update_last_refresh(n_intervals):
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
     Output("progress-text", "children"),
     Output("progress-bar", "color")],
    Input("status-interval", "n_intervals"),
)
def update_progress(n_intervals):
    """Update the progress indicators based on current progress"""
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
            "No active process running", 
            "primary"
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
            f"Process: {process_name}"
        ]),
        percentage, 
        f"{percentage}%" if percentage > 0 else "", 
        progress_text, 
        color
    ]

# Print message when starting the app
if __name__ == "__main__":
    print("Starting Healing Hands Data Automation dashboard at http://127.0.0.1:8050")
    app.run_server(debug=True)