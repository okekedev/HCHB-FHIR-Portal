README.md
markdown# Healing Hands Data Automation

A comprehensive dashboard and data automation toolkit for healthcare providers using the HCHB FHIR API. This application streamlines patient data collection, coordination note management, and appointment scheduling processes through an intuitive web interface.

## Features

- **Patient Demographics** - Extract and export comprehensive patient information
- **Coordination Notes** - Retrieve and organize care coordination documentation
- **Weekly Appointments** - Process and display scheduled patient visits
- **Workers Directory** - Manage healthcare worker information and assignments
- **Alert Media Integration** - Synchronize critical healthcare alerts with notification systems

## Getting Started

### Prerequisites

- Python 3.9+ 
- Git
- HCHB API credentials

### Installation

1. Clone the repository
git clone https://github.com/your-username/healing-hands-data-automation.git
cd healing-hands-data-automation

2. Create a virtual environment
python -m venv venv

3. Activate the virtual environment
- Windows (Git Bash): `source venv/Scripts/activate`
- Windows (PowerShell): `.\venv\Scripts\Activate`
- Linux/macOS: `source venv/bin/activate`

4. Install dependencies
pip install -r requirements.txt

5. Configure environment variables
cp .env.sample .env
Edit the .env file with your API credentials and configuration

### Running the Application

Start the Dash web server:
python app.py

The application will be available at http://localhost:8050

## Project Structure
healing-hands-data-automation/
├── app.py                 # Main Dash application
├── assets/                # CSS, images, and other static assets
├── components/            # Reusable Dash components
│   ├── card.py            # Dashboard card components
│   ├── navbar.py          # Navigation bar component
│   └── status.py          # Status indicator components
├── scripts/               # Data processing scripts
│   ├── alert_media_batch.py
│   ├── coordination_notes_csv.py
│   ├── patients_csv.py
│   ├── weekly_appointments_csv.py
│   └── workers_csv.py
├── utils/                 # Utility functions and helpers
│   ├── config.py          # Centralized configuration
│   ├── fhir_client.py     # FHIR API client
│   ├── logging_setup.py   # Logging configuration
│   ├── progress_tracker.py # Script progress monitoring
│   ├── script_runner.py   # Script execution utilities
│   └── sharepoint_client.py # SharePoint integration
└── output/                # Local output directory (git-ignored)

## API Integration

This application integrates with the HCHB FHIR R4 API for healthcare data management. The API provides access to:

- Patient demographics and clinical information
- Appointment and scheduling data
- Care team and provider information
- Clinical documentation
- Medication and treatment data

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- HCHB for providing the FHIR API
- Dash and Plotly for the interactive visualization framework
.env.sample
# API Authentication
CLIENT_ID=agency.client
RESOURCE_SECURITY_ID=your_security_id_here
AGENCY_SECRET=your_agency_secret_here
TOKEN_URL=https://idp.hchb.com/connect/token
API_BASE_URL=https://api.hchb.com/fhir/r4

# SharePoint Configuration
SP_CLIENT_ID=your_sharepoint_client_id
SP_CLIENT_SECRET=your_sharepoint_client_secret
SP_TENANT_ID=your_tenant_id
SP_SITE_NAME=OperationsTeam-Data
SP_FOLDER_PATH=Data

# Request Configuration
REQUEST_TIMEOUT=45
TOKEN_ROTATION_COUNT=200
MAX_RETRIES=3

# Processing Configuration
BATCH_SIZE=100
MAX_WORKERS=5
OUTPUT_DIRECTORY=output
PATIENT_BATCH_SIZE=1000
ENCOUNTER_BATCH_SIZE=100

# Files and Outputs
PATIENT_DATA_FILENAME=patient_data.csv
WEEKLY_APPOINTMENTS_FILENAME=weekly_appointments.csv
COORDINATION_NOTES_FILENAME=coordination_notes_master.csv
WORKERS_FILENAME=worker_data.csv
ALERT_MEDIA_FILENAME=alert_media_data.csv