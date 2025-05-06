import dash
from dash import dcc, html, callback, Input, Output, State
import dash_bootstrap_components as dbc
import time
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

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    assets_folder="assets"
)
app.title = "Healing Hands Data Automation"
server = app.server  # For deployment

# Dashboard layout
app.layout = html.Div([
    # Navigation bar at the top
    create_navbar(),
    
    # Main container
    dbc.Container([
        # Header
        html.Div([
            html.H1("Healing Hands Data Automation", className="display-4 text-center text-primary my-4"),
            html.Hr(className="my-4"),
        ], className="text-center"),
        
        # Main content
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
            ], width=6, className="mb-4"),
            
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
            ], width=6, className="mb-4"),
            
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
            ], width=6, className="mb-4"),
            
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
            ], width=6, className="mb-4"),
            
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
            ], width=6, className="mb-4"),
            
            # System Status Card
            dbc.Col([
                create_status_card()
            ], width=6, className="mb-4"),
        ]),
        
        # Footer
        html.Footer([
            html.Hr(),
            html.P("Healing Hands Data Automation Dashboard © 2025", className="text-center text-muted"),
        ], className="mt-4"),
    ], fluid=True, className="p-4"),
    
    # Store for tracking active processes
    dcc.Store(id="process-status"),
    
    # Interval for updating status
    dcc.Interval(id="status-interval", interval=1000, n_intervals=0),
])

# Register callbacks for all script cards
for script_id in ["alert-media", "coordination-notes", "patients", "weekly-appointments", "workers"]:
    @app.callback(
        Output(f"output-{script_id}", "children"),
        Output(f"output-{script_id}", "className"),
        Input(f"run-{script_id}", "n_clicks"),
        prevent_initial_call=True
    )
    def run_script_callback(n_clicks, script_id=script_id):
        if not n_clicks:
            return "", "mt-3 text-muted"
        
        # Get script information based on script_id
        script_paths = {
            "alert-media": "scripts.alert_media_batch",
            "coordination-notes": "scripts.coordination_notes_csv",
            "patients": "scripts.patients_csv",
            "weekly-appointments": "scripts.weekly_appointments_csv",
            "workers": "scripts.workers_csv"
        }
        
        script_path = script_paths.get(script_id)
        status, output = run_script_with_output(script_path)
        
        if status == "SUCCESS":
            return html.Div([
                html.P("Script executed successfully!", className="fw-bold"),
                html.P(f"Processed data at {time.strftime('%Y-%m-%d %H:%M:%S')}"),
            ]), "mt-3 text-success"
        else:
            return html.Div([
                html.P("Script execution failed!", className="fw-bold"),
                html.P(output),
            ]), "mt-3 text-danger"

# Callback for Last Refresh in Status Card
@app.callback(
    Output("last-refresh", "children"),
    Input("status-interval", "n_intervals"),
)
def update_last_refresh(n_intervals):
    return html.P(time.strftime("%Y-%m-%d %H:%M:%S"), className="text-info")

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
        return "None", 0, "", "No active process", "primary"
    
    # Format process name
    process_name = progress["process_name"]
    
    # Calculate percentage
    percentage = progress["percentage"]
    
    # Determine progress bar color based on status
    if progress["status"] == "completed":
        color = "success"
    elif progress["status"] == "error":
        color = "danger"
    else:
        color = "primary"
    
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
    return process_name, percentage, f"{percentage}%" if percentage > 0 else "", progress_text, color

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)