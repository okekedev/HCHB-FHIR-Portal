import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dotenv import load_dotenv
import os

# Import components
from components.navbar import create_navbar

# Import all callbacks (this will register them automatically)
from callbacks import register_all_callbacks

# Load environment variables
load_dotenv()

# Initialize the Dash app with Bootstrap theme and custom CSS
app = dash.Dash(
    __name__, 
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',
        'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Roboto+Mono&display=swap'
    ],
    assets_folder="assets",
    suppress_callback_exceptions=True
)

app.title = "HCHB FHIR Integration"
server = app.server  # For deployment

# Define script cards configuration for easier maintenance
script_configs = [
    {
        "title": "Alert Media Integration",
        "description": "Run the Alert Media batch process to sync healthcare alerts with the notification system.",
        "script_id": "alert-media",
        "script_path": "scripts.alert_media_batch",
        "api_details": [
            "This script extracts alert data from the HCHB FHIR API and prepares notifications for the Alert Media system.",
            "It processes critical patient alerts that require immediate attention from healthcare providers.",
            "API Endpoints Used:",
            "• Patient API - To retrieve patient demographic information",
            "• Care Team API - To identify assigned healthcare providers",
            "• Condition API - To identify critical patient conditions",
        ]
    },
    {
        "title": "Coordination Notes",
        "description": "Run the Coordination Notes extraction process to retrieve all care coordination notes.",
        "script_id": "coordination-notes",
        "script_path": "scripts.coordination_notes_csv",
        "api_details": [
            "This script retrieves coordination notes from the HCHB FHIR API, which contain important information about care coordination activities.",
            "It processes interdisciplinary team communications and patient care planning notes.",
            "API Endpoints Used:",
            "• Document Reference - Coordination Note API - For retrieving care coordination documentation",
            "• Episode of Care API - To link notes to specific care episodes",
            "• Practitioner API - To identify note authors and recipients",
        ]
    },
    {
        "title": "Patient Demographics",
        "description": "Run the Patients data extraction process to retrieve comprehensive patient information.",
        "script_id": "patients",
        "script_path": "scripts.patients_csv",
        "api_details": [
            "This script extracts comprehensive patient demographic and clinical information from the HCHB FHIR API.",
            "It includes personal details, contact information, diagnoses, and care episodes.",
            "API Endpoints Used:",
            "• Patient API - To retrieve comprehensive patient demographic information",
            "• Condition - Diagnoses API - To retrieve patient diagnoses",
            "• Episode of Care API - To retrieve patient care episodes",
            "• Related Person - Episode Contact API - To retrieve patient emergency contacts",
            "• Living Arrangement API - To retrieve patient living situation",
        ]
    },
    {
        "title": "Weekly Appointments",
        "description": "Run the Weekly Appointments extraction process to retrieve scheduled patient visits.",
        "script_id": "weekly-appointments",
        "script_path": "scripts.weekly_appointments_csv",
        "api_details": [
            "This script extracts weekly appointment data from the HCHB FHIR API.",
            "It includes scheduled visits, visit types, assigned caregivers, and visit details.",
            "API Endpoints Used:",
            "• Appointment - Patient Visit API - To retrieve scheduled patient visits",
            "• Appointment - Schedule API - To retrieve visit schedules",
            "• Care Team API - To identify assigned healthcare providers",
            "• Service Location API - To retrieve visit locations",
            "• Worker API - To retrieve caregiver information",
        ]
    },
    {
        "title": "Workers Directory",
        "description": "Run the Workers data extraction process to retrieve information about all healthcare workers.",
        "script_id": "workers",
        "script_path": "scripts.workers_csv",
        "api_details": [
            "This script extracts worker data from the HCHB FHIR API.",
            "It includes healthcare professionals, their roles, qualifications, and assignments.",
            "API Endpoints Used:",
            "• Worker API - To retrieve healthcare worker information",
            "• Worker Location API - To retrieve worker service areas",
            "• Organization - Team API - To retrieve team assignments",
            "• Organization - Branch API - To retrieve branch assignments",
        ]
    }
]

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
            # Card Content
            html.P(description, className="card-text mb-4"),
            dbc.Row([
                dbc.Col([
                    dbc.Button([
                        html.I(className="fas fa-play me-2"),
                        "Run Script"
                    ], 
                    id={"type": "run-script", "index": script_id}, 
                    color="primary", 
                    className="me-2"),
                ], width="auto"),
                dbc.Col([
                    dbc.Button([
                        html.I(className="fas fa-info-circle me-2"),
                        "API Details"
                    ], id={"type": "open-modal", "index": script_id}, color="secondary"),
                ], width="auto"),
            ], className="mb-4"),
            
            # Status indicator (initially hidden) - Fixed ID format to match callback expectations
            html.Div(
                id={"type": "script-status-indicator", "index": script_id},
                className="mb-3",
                style={"display": "none"}
            ),
            
            # Log container
            html.Div([
                html.Hr(className="my-3"),
                html.H5([
                    html.I(className="fas fa-terminal me-2"),
                    "Execution Log:"
                ], className="mb-3 d-flex align-items-center"),
                
                # Output area
                html.Div(
                    id={"type": "script-output", "index": script_id}, 
                    className="log-output",
                    style={"maxHeight": "250px", "overflowY": "auto"}
                )
            ], id={"type": "log-container", "index": script_id}, className="log-container", style={"display": "none"}),
        ]),
        
        # Modal for API Details
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
    ], 
    className="h-100 shadow", 
    id={"type": "script-card", "index": script_id})

# Dashboard layout
app.layout = html.Div([
    # Navigation bar at the top
    dbc.Navbar(
        dbc.Container([
            # Brand/logo with improved styling
            html.A(
                [
                    html.Img(src="/assets/logo.png", height="36px", className="me-3 d-inline-block align-middle"),
                    dbc.NavbarBrand("FHIR Data Automation", className="ms-2 d-inline-block align-middle"),
                ],
                href="/",
                style={"textDecoration": "none"},
                className="d-flex align-items-center"
            ),
            # Toggle button for mobile view
            dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
            # Simplified navigation - only showing Dashboard
            dbc.Collapse(
                dbc.Nav(
                    [
                        dbc.NavItem(dbc.NavLink("Dashboard", href="#", active=True)),
                    ],
                    navbar=True,
                    className="ms-auto align-items-center"
                ),
                id="navbar-collapse",
                navbar=True,
                is_open=False,
            ),
        ], fluid=True),
        color="primary",
        dark=True,
        className="mb-4 py-2 shadow",
        sticky="top",
    ),
    
    # Main container
    dbc.Container([
        # Active Processes Section (at the top)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4([
                            html.I(className="fas fa-tasks me-3"),
                            "Active Processes"
                        ], className="card-title d-flex align-items-center"),
                    ]),
                    dbc.CardBody([
                        html.Div(id="active-processes-list", children=[
                            html.P("No active processes", className="text-muted")
                        ], className="p-3")
                    ])
                ], className="shadow h-100")
            ], width=12, className="mb-5"),
        ]),
        
        # System Status Cards - Two column design
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="fas fa-chart-line me-3"),
                    "System Status"
                ], className="mb-5 mt-4 d-flex align-items-center"),
            ], width=12),
            
            # Left Status Column - API Status with simple spinner
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4([
                            html.I(className="fas fa-server me-3"),
                            "API Connection"
                        ], className="card-title d-flex align-items-center"),
                    ]),
                    dbc.CardBody([
                        html.Div([
                            html.Div([
                                html.Span("API Status: ", className="fw-bold me-2"),
                                html.Span([
                                    # This spinning circle will only appear on the API card
                                    html.Div(id="api-spinner", className="processing-spinner", 
                                           style={"display": "none"}),
                                    html.I(id="api-status-icon", className="fas fa-check-circle text-success me-2"),
                                    html.Span(id="api-status-text", children="Connected")
                                ], className="d-inline-flex align-items-center")
                            ], className="mb-4"),
                            html.Div([
                                html.Span("API URL: ", className="fw-bold me-2"),
                                html.Code(os.getenv('API_BASE_URL', 'https://api.hchb.com/fhir/r4'),
                                         className="bg-light rounded px-2 py-1")
                            ], className="mb-4"),
                            html.Div([
                                html.Span("Last Refresh: ", className="fw-bold me-2"),
                                html.Div(id="last-refresh", className="d-inline")
                            ], className="mb-4"),
                            html.Div([
                                html.Span("Environment: ", className="fw-bold me-2"),
                                html.Span(os.getenv('ENV', 'Production'), className="text-primary")
                            ], className="mb-2")
                        ], className="p-2")
                    ], className="p-4")
                ], className="shadow h-100")
            ], md=6, className="mb-5"),
            
            # Right Status Column - Simple progress display
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4([
                            html.I(className="fas fa-tachometer-alt me-3"),
                            "Processing Status"
                        ], className="card-title d-flex align-items-center"),
                    ]),
                    dbc.CardBody([
                        html.Div([
                            html.Div([
                                html.Span("Current Process: ", className="fw-bold me-2"),
                                html.Span(id="current-process", className="text-primary fw-bold")
                            ], className="mb-4"),
                            html.Div([
                                html.Span("Progress: ", className="fw-bold mb-2 d-block"),
                                dbc.Progress(
                                    id="progress-bar", 
                                    value=0, 
                                    label="0%",
                                    style={"height": "12px"}, 
                                    className="mb-3"
                                ),
                                html.P(id="progress-text", children="No active process", 
                                      className="text-muted fs-6")
                            ], className="mb-4"),
                            html.Div([
                                html.Span("Data Processed: ", className="fw-bold me-2"),
                                html.Div(id="data-processed", children="0 records", 
                                       className="text-primary")
                            ], className="mb-2")
                        ], className="p-2")
                    ], className="p-4")
                ], className="shadow h-100")
            ], md=6, className="mb-5"),
        ]),
        
        # Main content - Script cards
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="fas fa-tasks me-3"),
                    "Automation Tools"
                ], className="mb-5 mt-4 d-flex align-items-center"),
            ], width=12),
        ]),
        
        # First row of script cards (dynamically generated from config)
        dbc.Row([
            dbc.Col([
                create_script_card(**config)
            ], md=6, xl=4, className="mb-5")
            for config in script_configs[:3]  # First 3 cards in first row
        ], className="mb-3"),
        
        # Second row of script cards (dynamically generated from config)
        dbc.Row([
            dbc.Col([
                create_script_card(**config)
            ], md=6, className="mb-5")
            for config in script_configs[3:]  # Remaining cards in second row
        ], className="mb-5"),
        
        # Footer
        html.Footer([
            html.Hr(className="my-5"),
            dbc.Row([
                dbc.Col([
                    html.P([
                        "FHIR Data Automation Dashboard © 2025"
                    ], className="text-center text-muted mb-1"),
                    html.P([
                        "Powered by ",
                        html.A("HCHB FHIR API", href="#", className="text-decoration-none")
                    ], className="text-center text-muted small")
                ])
            ])
        ], className="mt-5"),
    ], fluid=True, className="p-5"),
    
    # Store for tracking active processes
    dcc.Store(id="process-status"),
    
    # Interval for updating status
    dcc.Interval(id="status-interval", interval=1000, n_intervals=0),
])

# Register all callbacks
register_all_callbacks(app)

# Print message when starting the app
if __name__ == "__main__":
    print("Starting FHIR Data Automation dashboard at http://127.0.0.1:8050")
    app.run_server(debug=True)