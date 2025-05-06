"""
Centralized configuration loading for Healing Hands automation scripts.
Loads configuration from .env file or environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Authentication
CLIENT_ID = os.getenv('CLIENT_ID')
RESOURCE_SECURITY_ID = os.getenv('RESOURCE_SECURITY_ID')
AGENCY_SECRET = os.getenv('AGENCY_SECRET')
TOKEN_URL = os.getenv('TOKEN_URL', 'https://idp.hchb.com/connect/token')
API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.hchb.com/fhir/r4')

# SharePoint Configuration
SP_CLIENT_ID = os.getenv('SP_CLIENT_ID')
SP_CLIENT_SECRET = os.getenv('SP_CLIENT_SECRET')
SP_TENANT_ID = os.getenv('SP_TENANT_ID')
SP_SITE_NAME = os.getenv('SP_SITE_NAME', 'OperationsTeam-Data')
SP_FOLDER_PATH = os.getenv('SP_FOLDER_PATH', 'Data')

# Request Configuration
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '1000'))
TOKEN_ROTATION_COUNT = int(os.getenv('TOKEN_ROTATION_COUNT', '200'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

# Processing Configuration
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '5'))
OUTPUT_DIRECTORY = os.getenv('OUTPUT_DIRECTORY', 'output')
PATIENT_BATCH_SIZE = int(os.getenv('PATIENT_BATCH_SIZE', '1000'))
ENCOUNTER_BATCH_SIZE = int(os.getenv('ENCOUNTER_BATCH_SIZE', '100'))

# Files and Outputs
PATIENT_DATA_FILENAME = os.getenv('PATIENT_DATA_FILENAME', 'patient_data.csv')
WEEKLY_APPOINTMENTS_FILENAME = os.getenv('WEEKLY_APPOINTMENTS_FILENAME', 'weekly_appointments.csv')
COORDINATION_NOTES_FILENAME = os.getenv('COORDINATION_NOTES_FILENAME', 'coordination_notes_master.csv')
WORKERS_FILENAME = os.getenv('WORKERS_FILENAME', 'worker_data.csv')
ALERT_MEDIA_FILENAME = os.getenv('ALERT_MEDIA_FILENAME', 'alert_media_data.csv')

# Validate that required configuration is present
required_vars = [
    'CLIENT_ID', 'RESOURCE_SECURITY_ID', 'AGENCY_SECRET',
    'SP_CLIENT_ID', 'SP_CLIENT_SECRET', 'SP_TENANT_ID'
]

missing_vars = [var for var in required_vars if not locals().get(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Ensure output directory exists
os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

def get_config():
    """
    Returns the configuration as a dictionary
    """
    return {
        'CLIENT_ID': CLIENT_ID,
        'RESOURCE_SECURITY_ID': RESOURCE_SECURITY_ID,
        'AGENCY_SECRET': AGENCY_SECRET,
        'TOKEN_URL': TOKEN_URL,
        'API_BASE_URL': API_BASE_URL,
        'SP_CLIENT_ID': SP_CLIENT_ID,
        'SP_CLIENT_SECRET': SP_CLIENT_SECRET,
        'SP_TENANT_ID': SP_TENANT_ID,
        'SP_SITE_NAME': SP_SITE_NAME,
        'SP_FOLDER_PATH': SP_FOLDER_PATH,
        'REQUEST_TIMEOUT': REQUEST_TIMEOUT,
        'TOKEN_ROTATION_COUNT': TOKEN_ROTATION_COUNT,
        'MAX_RETRIES': MAX_RETRIES,
        'BATCH_SIZE': BATCH_SIZE,
        'MAX_WORKERS': MAX_WORKERS,
        'OUTPUT_DIRECTORY': OUTPUT_DIRECTORY,
        'PATIENT_BATCH_SIZE': PATIENT_BATCH_SIZE,
        'ENCOUNTER_BATCH_SIZE': ENCOUNTER_BATCH_SIZE,
        'PATIENT_DATA_FILENAME': PATIENT_DATA_FILENAME,
        'WEEKLY_APPOINTMENTS_FILENAME': WEEKLY_APPOINTMENTS_FILENAME,
        'COORDINATION_NOTES_FILENAME': COORDINATION_NOTES_FILENAME,
        'WORKERS_FILENAME': WORKERS_FILENAME,
        'ALERT_MEDIA_FILENAME': ALERT_MEDIA_FILENAME,
    }

def print_config_summary(include_secrets=False):
    """
    Print a summary of the current configuration
    
    Args:
        include_secrets: Whether to include secret values in the output
    """
    print("\nCurrent Configuration:")
    print("-" * 50)
    
    # API Base Configuration
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Token URL: {TOKEN_URL}")
    
    # Authentication
    print(f"Client ID: {CLIENT_ID}")
    if include_secrets:
        print(f"Resource Security ID: {RESOURCE_SECURITY_ID}")
        print(f"Agency Secret: {AGENCY_SECRET}")
    else:
        print(f"Resource Security ID: {'*' * 8}")
        print(f"Agency Secret: {'*' * 8}")
    
    # SharePoint
    print(f"SharePoint Site: {SP_SITE_NAME}")
    print(f"SharePoint Folder: {SP_FOLDER_PATH}")
    
    # Request Configuration
    print(f"Request Timeout: {REQUEST_TIMEOUT} seconds")
    print(f"Token Rotation Count: {TOKEN_ROTATION_COUNT}")
    print(f"Max Retries: {MAX_RETRIES}")
    
    # Processing Configuration
    print(f"Batch Size: {BATCH_SIZE}")
    print(f"Patient Batch Size: {PATIENT_BATCH_SIZE}")
    print(f"Encounter Batch Size: {ENCOUNTER_BATCH_SIZE}")
    print(f"Max Workers: {MAX_WORKERS}")
    print(f"Output Directory: {OUTPUT_DIRECTORY}")
    
    # Filenames
    print("\nOutput Filenames:")
    print(f"Patient Data: {PATIENT_DATA_FILENAME}")
    print(f"Weekly Appointments: {WEEKLY_APPOINTMENTS_FILENAME}")
    print(f"Coordination Notes: {COORDINATION_NOTES_FILENAME}")
    print(f"Workers: {WORKERS_FILENAME}")
    print(f"Alert Media: {ALERT_MEDIA_FILENAME}")
    print("-" * 50)