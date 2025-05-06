"""
Streamlined FHIR Appointment Data Collector - SN11 Visits Only

This script collects filtered appointment information from the HCHB FHIR API including:
- Patient ID
- Appointment date/time
- Standard FHIR status
- Detailed HCHB status
- Service code (filtered to SN11 only)
- Service type
- Practitioner ID
- Visit Number

Uses shared utilities for:
- FHIR API client with token management
- SharePoint integration
- Standardized logging
- Centralized configuration
"""

import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# Import shared utilities
from utils.fhir_client import fhir_client
from utils.sharepoint_client import sharepoint_client
from utils.logging_setup import configure_logging
from utils.progress_tracker import ProgressTracker  # Add this import
from utils.config import (
    BATCH_SIZE, MAX_WORKERS, WEEKLY_APPOINTMENTS_FILENAME
)

# Configure logging
logger = configure_logging('weekly_appointments_csv')

def get_current_week_date_range():
    """Get the date range for the current week (Monday to Sunday)"""
    today = datetime.now()
    # Get the most recent Monday (0 = Monday in weekday())
    start_of_week = today - timedelta(days=today.weekday())
    # Get the upcoming Sunday
    end_of_week = start_of_week + timedelta(days=6)
    
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start_of_week.strftime("%Y-%m-%d"), end_of_week.strftime("%Y-%m-%d")

def get_appointments_for_day(date):
    """Get appointments for a specific day"""
    logger.info(f"Getting appointments for {date}...")
    
    # Parameters for the search
    params = {
        "date": f"eq{date}",  # Exact date filter
        "_count": BATCH_SIZE,
        "_sort": "date",      # Sort by date
        # Filter for only SN11 service code
        "service-type": "SN11"
    }
    
    # Use the FHIR client to get all appointments for this day
    appointments = fhir_client.get_all_pages("Appointment", params)
    
    logger.info(f"Found {len(appointments)} appointments for {date}")
    return appointments

def get_appointments_for_week(start_date, end_date, progress_tracker=None):
    """Get appointments for the given date range using controlled concurrent processing"""
    logger.info(f"Getting appointments from {start_date} to {end_date} with concurrent processing...")
    
    # Generate list of dates in the range
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    date_list = []
    
    current = start
    while current <= end:
        date_list.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    all_appointments = []
    
    # Update progress tracker with total dates to process
    if progress_tracker:
        progress_tracker.total_items = len(date_list)
        progress_tracker.update(0, f"Processing {len(date_list)} days of appointments")
    
    # Process dates in chunks to reduce load on the API
    max_concurrent = min(MAX_WORKERS, len(date_list))
    for i in range(0, len(date_list), max_concurrent):
        chunk = date_list[i:i + max_concurrent]
        logger.info(f"Processing dates {chunk}...")
        
        if progress_tracker:
            progress_tracker.update(i, f"Processing dates {i+1}-{min(i+max_concurrent, len(date_list))} of {len(date_list)}")
        
        # Process this chunk of days concurrently
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Map each date to the appointment retrieval function
            future_to_date = {executor.submit(get_appointments_for_day, date): date for date in chunk}
            
            # Process results as they complete
            for future in future_to_date:
                date = future_to_date[future]
                try:
                    appointments = future.result()
                    all_appointments.extend(appointments)
                    logger.info(f"Successfully processed appointments for {date}")
                except Exception as e:
                    logger.error(f"Error processing appointments for {date}: {e}")
                    # Log the full traceback for debugging
                    import traceback
                    logger.error(traceback.format_exc())
    
    # Update progress tracker with completion of appointment retrieval
    if progress_tracker:
        progress_tracker.update(len(date_list), f"Retrieved {len(all_appointments)} appointments for the week")
    
    logger.info(f"Found a total of {len(all_appointments)} appointments for the week")
    return all_appointments

def process_appointment(appointment):
    """
    Process a single appointment to extract required fields
    
    Args:
        appointment: Appointment resource to process
        
    Returns:
        Dictionary with processed appointment data
    """
    appointment_id = appointment.get("id", "")
    
    # Initialize fields
    patient_id = ""
    practitioner_id = ""
    appointment_datetime = ""
    standard_status = appointment.get("status", "")
    status_value = ""  # Status value from extension
    service_code = ""  # Service code
    service_type = ""  # Service type display
    visit_number = ""
    
    # Get status value from extension[4] based on provided screenshot
    # Look specifically for the extension with detailed-status
    if "extension" in appointment:
        for ext in appointment["extension"]:
            # Check for extension[4] which contains StatusValue
            if ext.get("url") == "https://api.hchb.com/fhir/r4/StructureDefinition/detailed-status":
                # Look for nested extension with url "StatusValue"
                if isinstance(ext.get("extension"), list):
                    for nested_ext in ext["extension"]:
                        if nested_ext.get("url") == "StatusValue":
                            status_value = nested_ext.get("valueString", "")
                            break
            
            # Fallback to direct StatusValue check 
            elif ext.get("url") == "StatusValue":
                status_value = ext.get("valueString", "")
                break
    
    # Get patient and practitioner references from participants
    if "participant" in appointment:
        for participant in appointment["participant"]:
            # Check if this participant has an actor reference
            if "actor" in participant and "reference" in participant["actor"]:
                actor_ref = participant["actor"]["reference"]
                
                # Check for patient reference
                if actor_ref.startswith("Patient/"):
                    patient_id = actor_ref.replace("Patient/", "")
                
                # Check for practitioner reference
                elif actor_ref.startswith("Practitioner/"):
                    # Check if this is specifically the performer practitioner
                    is_performer = False
                    
                    # Look for type coding with code "PRF" (Performer)
                    if "type" in participant:
                        for type_item in participant["type"]:
                            if "coding" in type_item:
                                for coding in type_item["coding"]:
                                    if coding.get("code") == "PRF" or coding.get("display") == "Performer":
                                        is_performer = True
                                        break
                    
                    # If this is the performer practitioner or if no specific type is defined
                    if is_performer or "type" not in participant:
                        practitioner_id = actor_ref.replace("Practitioner/", "")
                
                # Skip location references entirely - don't process them at all
    
    # Also check for patient in extensions if not found in participants
    if not patient_id and "extension" in appointment:
        for extension in appointment["extension"]:
            # Look for subject extension which contains patient reference
            if extension.get("url") == "https://api.hchb.com/fhir/r4/StructureDefinition/subject":
                if "valueReference" in extension and "reference" in extension["valueReference"]:
                    patient_ref = extension["valueReference"]["reference"]
                    if patient_ref.startswith("Patient/"):
                        patient_id = patient_ref.replace("Patient/", "")
    
    # Get visit number from extension[2] based on provided screenshot
    if "extension" in appointment:
        for extension in appointment["extension"]:
            if extension.get("url") == "https://api.hchb.com/fhir/r4/StructureDefinition/entity-index":
                if "valueInteger" in extension:
                    visit_number = str(extension.get("valueInteger", ""))
                    break
    
    # Get appointment datetime and ensure proper formatting
    if "start" in appointment:
        raw_datetime = appointment["start"]
        try:
            # Parse and reformat to ensure consistent datetime format
            parsed_dt = datetime.fromisoformat(raw_datetime.replace('Z', '+00:00'))
            appointment_datetime = parsed_dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            # If parsing fails, use the original format
            appointment_datetime = raw_datetime
    
    # Get service type and code
    if "serviceType" in appointment:
        service_types = appointment["serviceType"]
        if service_types and isinstance(service_types, list) and len(service_types) > 0:
            # Get the first service type
            service_type_obj = service_types[0]
            # Check for text first, then try coding display
            if "text" in service_type_obj:
                service_type = service_type_obj["text"]
            
            # Extract service code from coding
            if "coding" in service_type_obj:
                codings = service_type_obj["coding"]
                if codings and isinstance(codings, list) and len(codings) > 0:
                    coding = codings[0]
                    if "code" in coding:
                        service_code = coding["code"]
                    if "display" in coding and not service_type:
                        service_type = coding["display"]
    
    # Create result with processed data - ONLY required fields
    result = {
        "appointmentId": appointment_id,
        "patientId": patient_id,
        "practitionerId": practitioner_id,
        "visitNumber": visit_number,
        "appointmentDatetime": appointment_datetime,
        "status": standard_status,
        "statusValue": status_value,
        "serviceCode": service_code,
        "serviceType": service_type,
        "collectionTimestamp": datetime.now().isoformat()
    }
    
    return result

def extract_appointment_data(appointments, progress_tracker=None):
    """Extract relevant data from appointments with enhanced performance"""
    logger.info(f"Processing {len(appointments)} appointments with {MAX_WORKERS} workers...")
    
    # Update progress tracker
    if progress_tracker:
        progress_tracker.update(progress_tracker.processed_items, 
                               f"Processing {len(appointments)} appointments")
    
    # Process appointments in parallel - NO location processing
    processed_count = 0
    results = []
    
    # Process in batches to provide progress updates
    batch_size = max(10, len(appointments) // 10)  # Process in roughly 10 batches for updates
    for i in range(0, len(appointments), batch_size):
        batch = appointments[i:i+batch_size]
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Map the process_appointment function to the batch
            batch_results = list(executor.map(process_appointment, batch))
            results.extend(batch_results)
        
        # Update processed count and progress
        processed_count += len(batch)
        if progress_tracker:
            progress_tracker.update(
                progress_tracker.processed_items,
                f"Processed {processed_count} of {len(appointments)} appointments"
            )
    
    # Filter out None results
    appointment_data = [result for result in results if result]
    
    # Filter for SN11 appointments only (double-check just in case API filter didn't work)
    appointment_data = [app for app in appointment_data if app.get("serviceCode") == "SN11"]
    
    # Log status and service code distributions
    status_counts = {}
    status_value_counts = {}
    service_code_counts = {}
    
    for app in appointment_data:
        # Track statuses
        status = app.get("status", "unknown")
        if status not in status_counts:
            status_counts[status] = 0
        status_counts[status] += 1
        
        # Track status values
        status_value = app.get("statusValue", "unknown")
        if status_value not in status_value_counts:
            status_value_counts[status_value] = 0
        status_value_counts[status_value] += 1
        
        # Track service codes
        svc_code = app.get("serviceCode", "unknown") 
        if svc_code not in service_code_counts:
            service_code_counts[svc_code] = 0
        service_code_counts[svc_code] += 1
    
    # Log the counts
    logger.info(f"Status counts from processed data: {status_counts}")
    logger.info(f"Status value counts from processed data: {status_value_counts}")
    logger.info(f"Service code counts from processed data: {service_code_counts}")
    logger.info(f"Successfully processed {len(appointment_data)} SN11 appointments")
    
    # Update progress tracker
    if progress_tracker:
        progress_tracker.update(progress_tracker.processed_items,
                              f"Extracted {len(appointment_data)} SN11 appointments")
    
    return appointment_data

def main():
    """Main function to run the script"""
    try:
        # Record start time for performance tracking
        start_time = datetime.now()
        logger.info(f"Script started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Initialize progress tracker
        progress = ProgressTracker("Weekly Appointments")
        
        # Get date range for current week
        start_date, end_date = get_current_week_date_range()
        logger.info(f"Fetching appointments for the current week ({start_date} to {end_date})")
        progress.update(0, f"Fetching appointments for {start_date} to {end_date}")
        
        # Step 1: Get appointments for the current week
        appointments = get_appointments_for_week(start_date, end_date, progress)
        
        if appointments:
            # Update progress
            progress.update(progress.processed_items, f"Retrieved {len(appointments)} appointments")
            
            # Step 2: Extract appointment data
            appointment_data = extract_appointment_data(appointments, progress)
            
            if appointment_data:
                try:
                    # Update progress
                    progress.update(progress.processed_items, f"Uploading {len(appointment_data)} appointments to SharePoint")
                    
                    # Define fieldnames for CSV
                    fieldnames = [
                        "appointmentId", 
                        "patientId",
                        "practitionerId",
                        "visitNumber",
                        "appointmentDatetime", 
                        "status", 
                        "statusValue",
                        "serviceCode",
                        "serviceType",
                        "collectionTimestamp"
                    ]
                    
                    # Step 3: Upload the data to SharePoint
                    sharepoint_client.upload_csv(appointment_data, WEEKLY_APPOINTMENTS_FILENAME, fieldnames)
                    logger.info(f"Appointment data successfully uploaded to SharePoint as '{WEEKLY_APPOINTMENTS_FILENAME}'")
                    print(f"\nSuccessfully uploaded {len(appointment_data)} appointments to SharePoint as '{WEEKLY_APPOINTMENTS_FILENAME}'")
                    
                    # Complete progress tracking
                    progress.complete(f"Successfully uploaded {len(appointment_data)} appointments")
                    
                except Exception as e:
                    logger.error(f"Error with SharePoint upload: {e}")
                    logger.error("Unable to upload data to SharePoint")
                    print(f"\nError uploading to SharePoint: {e}")
                    
                    # Update progress with error
                    progress.set_error(f"SharePoint upload failed: {str(e)}")
                    return False
            else:
                logger.warning("No appointment data extracted")
                print("\nNo appointment data extracted")
                progress.complete("No appointment data extracted")
        else:
            logger.warning("No appointments found for the current week")
            print("\nNo appointments found for the current week")
            progress.complete("No appointments found for the current week")
        
        # Record end time and calculate duration
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Script completed at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Total execution time: {duration.total_seconds():.2f} seconds")
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"\nError occurred: {e}")
        
        # Update progress with error if progress tracker exists
        if 'progress' in locals():
            progress.set_error(str(e))
            
        return False

if __name__ == "__main__":
    main()