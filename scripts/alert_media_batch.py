"""
FHIR Patient Data Collector Script - Optimized Version

This script efficiently collects patient data from FHIR R4 APIs and exports it to CSV.
Fields collected: LastName, FirstName, MI, Street, City, State, Zip, County, Phone, O2

Uses shared utilities for:
- FHIR API client with token management
- SharePoint integration
- Standardized logging
- Progress tracking
- Centralized configuration
"""

import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import re
import os

# Import shared utilities
from utils.fhir_client import fhir_client
from utils.sharepoint_client import sharepoint_client
from utils.logging_setup import configure_logging
from utils.progress_tracker import ProgressTracker
from utils.config import (
    BATCH_SIZE, MAX_WORKERS, PATIENT_BATCH_SIZE, OUTPUT_DIRECTORY
)

# Configure logging
logger = configure_logging('patients_csv')

def normalize_phone_number(phone_number):
    """
    Normalize phone number format to ensure consistency.
    
    Args:
        phone_number: Phone number string to normalize
        
    Returns:
        Normalized phone number string (###-###-####)
    """
    if not phone_number:
        return ""
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone_number)
    
    # Check if we have 10 digits (standard US format)
    if len(digits_only) == 10:
        return f"{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}"
    # Check if we have 11 digits with leading 1 (US with country code)
    elif len(digits_only) == 11 and digits_only[0] == '1':
        return f"{digits_only[1:4]}-{digits_only[4:7]}-{digits_only[7:]}"
    # Return original if format doesn't match expected patterns
    else:
        logger.warning(f"Unusual phone number format: {phone_number}")
        return phone_number

def get_all_active_patients(progress_tracker=None):
    """
    Get all active patients with birthdate using pagination.
    
    Args:
        progress_tracker: Optional ProgressTracker instance
        
    Returns:
        List of patient resources with birthdate
    """
    logger.info("Starting retrieval of all active patients...")
    
    # Update progress tracker
    if progress_tracker:
        progress_tracker.update(0, "Retrieving active patients")
    
    # Parameters for the search
    params = {
        "active": "true",             # Only get active patients
        "_count": PATIENT_BATCH_SIZE, # Number of patients per page
    }
    
    # Use the FHIR client to get all patients
    all_patients = fhir_client.get_all_pages("Patient", params)
    
    # Filter patients with birthdate
    patients_with_birthdate = []
    patients_without_birthdate = 0
    
    for patient in all_patients:
        if "birthDate" in patient and patient["birthDate"]:
            patients_with_birthdate.append(patient)
        else:
            patients_without_birthdate += 1
    
    # Log the results
    logger.info(f"Completed retrieval of active patients:")
    logger.info(f"  - {len(patients_with_birthdate)} active patients with birthdate")
    logger.info(f"  - {patients_without_birthdate} patients without birthdate (filtered out)")
    
    # Update progress tracker
    if progress_tracker:
        progress_tracker.update(progress_tracker.processed_items, 
                               f"Retrieved {len(patients_with_birthdate)} active patients")
    
    return patients_with_birthdate

def get_patient_locations_batch(patient_ids, progress_tracker=None):
    """
    Get location information for a batch of patients by finding their most
    recent encounters and associated location details.
    
    Args:
        patient_ids: List of patient IDs
        progress_tracker: Optional ProgressTracker instance
        
    Returns:
        Dictionary mapping patient IDs to location data
    """
    logger.info(f"Getting location data for {len(patient_ids)} patients in batches of {BATCH_SIZE}...")
    
    # Update progress tracker
    if progress_tracker:
        progress_tracker.update(progress_tracker.processed_items, 
                               f"Getting location data for {len(patient_ids)} patients")
    
    # Create batches for processing
    batches = [patient_ids[i:i+BATCH_SIZE] for i in range(0, len(patient_ids), BATCH_SIZE)]
    patient_locations = {}
    location_cache = {}  # Cache location details to avoid redundant API calls
    
    # Process batches with ThreadPoolExecutor
    batch_count = 0
    for batch in batches:
        batch_count += 1
        logger.info(f"Processing location batch {batch_count}/{len(batches)}")
        
        # Update progress tracker
        if progress_tracker:
            progress_tracker.update(progress_tracker.processed_items, 
                                   f"Processing location batch {batch_count}/{len(batches)}")
        
        # Process batch in parallel
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Map each patient ID to a function that gets its location
            future_to_patient = {
                executor.submit(_get_patient_location, patient_id, location_cache): patient_id 
                for patient_id in batch
            }
            
            # Process completed tasks
            for future in future_to_patient:
                patient_id = future_to_patient[future]
                try:
                    location_data = future.result()
                    if location_data:
                        patient_locations[patient_id] = location_data
                except Exception as e:
                    logger.error(f"Error processing location for patient {patient_id}: {e}")
    
    # Log results
    locations_found = sum(1 for loc in patient_locations.values() if loc.get("county"))
    logger.info(f"Found location data for {locations_found} out of {len(patient_ids)} patients")
    
    # Update progress tracker
    if progress_tracker:
        progress_tracker.update(progress_tracker.processed_items, 
                               f"Found location data for {locations_found} patients")
    
    return patient_locations

def _get_patient_location(patient_id, location_cache):
    """
    Get location data for a single patient.
    
    Args:
        patient_id: The patient ID
        location_cache: Shared cache for location resources
        
    Returns:
        Dictionary with location data or None if not found
    """
    try:
        # First, get the patient's recent encounters
        encounters = _get_patient_encounters(patient_id)
        
        if encounters:
            # Extract location from the most recent encounter with a location
            location_id = None
            for encounter in encounters:
                if "location" in encounter and encounter["location"]:
                    for loc in encounter["location"]:
                        if "location" in loc and "reference" in loc["location"]:
                            location_ref = loc["location"]["reference"]
                            if location_ref.startswith("Location/"):
                                location_id = location_ref.replace("Location/", "")
                                break
                    if location_id:
                        break
            
            # If we found a location reference, get the location details
            if location_id:
                # Check cache first
                if location_id in location_cache:
                    county, phone = location_cache[location_id]
                else:
                    # Get location details from API
                    location = fhir_client.get_resource("Location", location_id)
                    county, phone = _extract_location_details(location)
                    location_cache[location_id] = (county, phone)
                
                # If we didn't get a phone from the location, try the patient resource
                if not phone:
                    patient_phone = _get_patient_phone(patient_id)
                    phone = patient_phone
                
                # Store location data
                return {
                    "county": county,
                    "phone": phone,
                    "location_id": location_id
                }
            else:
                # No location in encounters, try to get at least phone from patient
                patient_phone = _get_patient_phone(patient_id)
                if patient_phone:
                    return {
                        "county": None,
                        "phone": patient_phone,
                        "location_id": None
                    }
        else:
            # No encounters found, try to get at least phone from patient
            patient_phone = _get_patient_phone(patient_id)
            if patient_phone:
                return {
                    "county": None,
                    "phone": patient_phone,
                    "location_id": None
                }
            
    except Exception as e:
        logger.error(f"Error processing location for patient {patient_id}: {e}")
    
    return None

def _get_patient_encounters(patient_id):
    """
    Get recent encounters for a patient.
    
    Args:
        patient_id: The patient ID
        
    Returns:
        List of encounter resources sorted by date (most recent first)
    """
    try:
        # Parameters to get multiple recent encounters
        params = {
            "subject": f"Patient/{patient_id}",
            "_sort": "-date",         # Sort by date descending (most recent first)
            "_count": "10"            # Get several recent encounters
        }
        
        # Use FHIR client to get encounters
        bundle = fhir_client.get_resource("Encounter", params=params)
        
        encounters = []
        
        # Check if encounters were found
        if "entry" in bundle and bundle["entry"]:
            for entry in bundle["entry"]:
                if "resource" in entry and entry["resource"]["resourceType"] == "Encounter":
                    encounter = entry["resource"]
                    encounters.append(encounter)
        
        return encounters
        
    except Exception as e:
        logger.error(f"Error getting encounters for patient {patient_id}: {e}")
        return []

def _extract_location_details(location):
    """
    Extract county and phone from a location resource.
    
    Args:
        location: Location resource
        
    Returns:
        Tuple of (county, phone)
    """
    if not location:
        return (None, None)
    
    # Extract county from district field in address
    county = None
    if "address" in location and "district" in location["address"]:
        county = location["address"]["district"]
    
    # Extract phone number
    phone = None
    if "telecom" in location:
        for telecom in location["telecom"]:
            if telecom.get("system") == "phone":
                phone = normalize_phone_number(telecom.get("value"))
                break
    
    return (county, phone)

def _get_patient_phone(patient_id):
    """
    Get a phone number directly from the patient resource.
    
    Args:
        patient_id: The patient ID
        
    Returns:
        Phone number string or None if not found
    """
    try:
        # Get patient resource
        patient = fhir_client.get_resource("Patient", patient_id)
        
        # Try to get phone from telecom section
        if "telecom" in patient:
            # First prioritize home phone
            for telecom in patient["telecom"]:
                if telecom.get("system") == "phone" and telecom.get("use") == "home":
                    return normalize_phone_number(telecom.get("value"))
            
            # Then try any phone
            for telecom in patient["telecom"]:
                if telecom.get("system") == "phone":
                    return normalize_phone_number(telecom.get("value"))
        
        # No phone number found
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving phone number for patient {patient_id}: {e}")
        return None

def get_patient_o2_status_batch(patient_ids, progress_tracker=None):
    """
    Check if patients have oxygen-related medication in batches.
    
    Args:
        patient_ids: List of patient IDs
        progress_tracker: Optional ProgressTracker instance
        
    Returns:
        Dictionary mapping patient IDs to O2 status
    """
    logger.info(f"Checking O2 status for {len(patient_ids)} patients in batches of {BATCH_SIZE}...")
    
    # Update progress tracker
    if progress_tracker:
        progress_tracker.update(progress_tracker.processed_items, 
                               f"Checking O2 status for {len(patient_ids)} patients")
    
    # Known O2 medication IDs and keywords
    known_o2_medication_ids = [
        "zxiqm1e9pad",  # OXYGEN
        "ezi36d75lcl",  # O2 - OXYGEN
        "mpi76en0iq",   # oxygen gas for inhalation
        "mpi7d4qr3sq",  # O2 - OXYGEN - PORTABLE
        "67i957z4xho"   # O2 - OXYGEN - CPAP
    ]
    
    o2_keywords = [
        "oxygen", "o2", "concentrator", "portable oxygen", "continuous oxygen",
        "liquid oxygen", "nasal cannula", "oxygen tank", "cpap", "bipap", 
        "ventilator", "respiratory", "breathing", "inhalation", "home oxygen"
    ]
    
    dosage_keywords = [
        "continuous", "prn", "as needed", "as directed", "bedtime", "daily",
        "liters", "lpm", "l/min", "nocturnal", "o2 sat"
    ]
    
    # Create batches for processing
    batches = [patient_ids[i:i+BATCH_SIZE] for i in range(0, len(patient_ids), BATCH_SIZE)]
    o2_status = {patient_id: False for patient_id in patient_ids}  # Initialize all to False
    match_reasons = {}  # Track matches for logging
    
    # Process batches with ThreadPoolExecutor
    batch_count = 0
    for batch in batches:
        batch_count += 1
        logger.info(f"Processing O2 status batch {batch_count}/{len(batches)}")
        
        # Update progress tracker
        if progress_tracker:
            progress_tracker.update(progress_tracker.processed_items, 
                                   f"Processing O2 status batch {batch_count}/{len(batches)}")
        
        # Process this batch in parallel
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Create a function that checks O2 status for each patient
            future_to_patient = {
                executor.submit(
                    _check_patient_o2_status, 
                    patient_id, 
                    known_o2_medication_ids,
                    o2_keywords,
                    dosage_keywords
                ): patient_id for patient_id in batch
            }
            
            # Process results as they complete
            for future in future_to_patient:
                patient_id = future_to_patient[future]
                try:
                    has_o2, match_reason = future.result()
                    o2_status[patient_id] = has_o2
                    if has_o2:
                        match_reasons[patient_id] = match_reason
                except Exception as e:
                    logger.error(f"Error checking O2 status for patient {patient_id}: {e}")
    
    # Count patients with O2
    patients_with_o2 = sum(1 for status in o2_status.values() if status)
    logger.info(f"Found {patients_with_o2} patients with oxygen medication")
    
    # Log some sample matches for debugging
    if match_reasons:
        logger.info("Sample oxygen medication matches:")
        sample_count = min(5, len(match_reasons))
        for patient_id, reason in list(match_reasons.items())[:sample_count]:
            logger.info(f"  Patient {patient_id}: {reason}")
    
    # Update progress tracker
    if progress_tracker:
        progress_tracker.update(progress_tracker.processed_items, 
                               f"Found {patients_with_o2} patients with oxygen")
    
    return o2_status

def _check_patient_o2_status(patient_id, known_o2_medication_ids, o2_keywords, dosage_keywords):
    """
    Check if a patient has oxygen-related medication.
    
    Args:
        patient_id: The patient ID
        known_o2_medication_ids: List of known medication IDs for oxygen
        o2_keywords: List of keywords that indicate oxygen medication
        dosage_keywords: List of dosage keywords related to oxygen
        
    Returns:
        Tuple of (has_oxygen, match_reason)
    """
    try:
        # Query to get active AND completed medications for this patient
        params = {
            "patient": f"Patient/{patient_id}",
            # Include both active and completed (recent history might be relevant)
            "status": "active,completed",
            "_count": "100"  # Increase to get more potential matches
        }
        
        # Get medication requests for this patient
        med_requests = fhir_client.get_resources("MedicationRequest", params)
        
        for med_request in med_requests:
            # Check for known medication IDs
            med_id = med_request.get("id", "")
            if med_id in known_o2_medication_ids:
                return True, f"Matched known ID: {med_id}"
            
            # Check medication display name
            if "medicationCodeableConcept" in med_request:
                med_concept = med_request["medicationCodeableConcept"]
                
                # Check text field
                med_name = med_concept.get("text", "").lower()
                if any(keyword.lower() in med_name for keyword in o2_keywords):
                    return True, f"Matched name: {med_name}"
                
                # Check coding array for oxygen codes
                if "coding" in med_concept:
                    for coding in med_concept["coding"]:
                        code = coding.get("code", "")
                        display = coding.get("display", "").lower()
                        
                        # If code matches known pattern for oxygen
                        if (code.startswith("O2") or 
                            "oxygen" in display or 
                            "o2" in display.split() or
                            any(keyword.lower() in display for keyword in o2_keywords)):
                            return True, f"Matched coding: {display}"
            
            # Check the dosage instructions
            if "dosageInstruction" in med_request:
                for instruction in med_request["dosageInstruction"]:
                    # Check text field for dosage
                    if "text" in instruction:
                        instruction_text = instruction["text"].lower()
                        
                        # If medication name doesn't have oxygen but dosage mentions it
                        if any(keyword.lower() in instruction_text for keyword in o2_keywords):
                            return True, f"Matched dosage text: {instruction_text[:30]}..."
                        
                        # Check for dosage patterns that suggest oxygen
                        if ("medicationCodeableConcept" in med_request and
                            "text" in med_request["medicationCodeableConcept"]):
                            med_name = med_request["medicationCodeableConcept"]["text"].lower()
                            if (any(kw in instruction_text for kw in dosage_keywords) and
                                (med_name.startswith("o2") or "oxygen" in med_name)):
                                return True, f"Matched dosage pattern: {instruction_text[:30]}..."
            
            # Check category
            if "category" in med_request:
                for category in med_request["category"]:
                    if "coding" in category:
                        for coding in category["coding"]:
                            display = coding.get("display", "").lower()
                            if "respiratory" in display or "oxygen" in display:
                                return True, f"Matched category: {display}"
            
            # Check notes
            if "note" in med_request:
                for note in med_request["note"]:
                    if "text" in note:
                        note_text = note["text"].lower()
                        if any(keyword.lower() in note_text for keyword in o2_keywords):
                            return True, f"Matched note text: {note_text[:30]}..."
        
        # No oxygen medication found
        return False, ""
        
    except Exception as e:
        logger.error(f"Error checking O2 medication for patient {patient_id}: {e}")
        return False, ""

def prepare_patient_data(patients, patient_locations, o2_status, progress_tracker=None):
    """
    Prepare patient data with location information and O2 status.
    
    Args:
        patients: List of patient resources
        patient_locations: Dictionary mapping patient IDs to location data
        o2_status: Dictionary mapping patient IDs to O2 status
        progress_tracker: Optional ProgressTracker instance
        
    Returns:
        Tuple of (complete_data_list, missing_data_list)
    """
    logger.info(f"Preparing data for {len(patients)} patients...")
    
    # Update progress tracker
    if progress_tracker:
        progress_tracker.update(progress_tracker.processed_items, 
                               f"Preparing data for {len(patients)} patients")
    
    complete_data_list = []
    missing_data_list = []
    
    # Process patients in batches for better progress tracking
    batch_size = max(100, len(patients) // 10)  # Process in roughly 10 batches
    for i in range(0, len(patients), batch_size):
        batch = patients[i:i+batch_size]
        
        for patient in batch:
            patient_id = patient.get("id", "")
            
            # Extract patient name components
            last_name = ""
            first_name = ""
            middle_initial = ""
            
            if "name" in patient and patient["name"]:
                official_name = next((n for n in patient["name"] if n.get("use") == "official"), 
                                    patient["name"][0] if patient["name"] else None)
                
                if official_name:
                    # Get last name
                    last_name = official_name.get("family", "")
                    
                    # Get first name and middle initial
                    given_names = official_name.get("given", [])
                    if given_names and len(given_names) > 0:
                        first_name = given_names[0]
                        
                        # Middle initial
                        if len(given_names) > 1:
                            middle_name = given_names[1]
                            middle_initial = middle_name[0] if middle_name else ""
            
            # Extract address components
            street = ""
            city = ""
            state = ""
            zip_code = ""
            
            if "address" in patient and patient["address"]:
                address = patient["address"][0]
                
                # Street (first line of address)
                if "line" in address and address["line"]:
                    street = address["line"][0]
                
                city = address.get("city", "")
                state = address.get("state", "")
                zip_code = address.get("postalCode", "")
            
            # Get location data
            county = ""
            phone = ""
            has_complete_data = False
            
            if patient_id in patient_locations:
                location_data = patient_locations[patient_id]
                county = location_data.get("county", "")
                phone = location_data.get("phone", "")
                has_complete_data = bool(county and phone)
            
            # Get O2 status - Use "Yes" for Y and leave blank for N
            o2_status_value = "Yes" if o2_status.get(patient_id, False) else ""
            
            # Create patient data dictionary
            patient_data = {
                "PatientId": patient_id,
                "LastName": last_name,
                "FirstName": first_name,
                "MI": middle_initial,
                "Street": street,
                "City": city,
                "State": state,
                "Zip": zip_code,
                "County": county or "",
                "Phone": phone or "",
                "O2": o2_status_value
            }
            
            # Add to appropriate list
            if has_complete_data:
                complete_data_list.append(patient_data)
            else:
                missing_data_list.append(patient_data)
        
        # Update progress if we have a tracker
        if progress_tracker:
            processed = min(i + batch_size, len(patients))
            progress_tracker.update(progress_tracker.processed_items, 
                                   f"Processed {processed}/{len(patients)} patients")
    
    logger.info(f"Prepared data for {len(patients)} patients")
    logger.info(f"  - {len(complete_data_list)} patients have complete data")
    logger.info(f"  - {len(missing_data_list)} patients have missing location data")
    
    # Final progress update
    if progress_tracker:
        progress_tracker.update(progress_tracker.processed_items, 
                               f"Finished preparation: {len(complete_data_list)} complete, "
                               f"{len(missing_data_list)} with missing data")
    
    return complete_data_list, missing_data_list

def main():
    """Main function to run the script"""
    try:
        # Record start time for performance tracking
        start_time = datetime.now()
        logger.info(f"Script started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Initialize progress tracker
        progress = ProgressTracker("Patient Data Collection")
        progress.update(0, "Starting patient data collection process")
        
        # Step 1: Get all active patients with birthdate
        all_patients = get_all_active_patients(progress)
        
        if all_patients:
            # Step 2: Get patient IDs
            patient_ids = [patient.get("id") for patient in all_patients if "id" in patient]
            
            # Step 3: Get location details for patients in batches
            patient_locations = get_patient_locations_batch(patient_ids, progress)
            
            # Step 4: Get O2 status for patients in batches
            o2_status = get_patient_o2_status_batch(patient_ids, progress)
            
            # Step 5: Prepare patient data
            complete_data, missing_data = prepare_patient_data(
                all_patients, patient_locations, o2_status, progress
            )
            
            # Step 6: Generate timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Step 7: Save data
            if complete_data or missing_data:
                progress.update(progress_tracker.processed_items, 
                               f"Saving data for {len(complete_data) + len(missing_data)} patients")
                
                try:
                    # Define columns for the CSV
                    columns = [
                        "LastName", "FirstName", "MI", "Street", "City", "State", "Zip", 
                        "County", "Phone", "O2"
                    ]
                    
                    # Try to upload to SharePoint first
                    all_data = complete_data + missing_data
                    filename = f"patients_data_{timestamp}.csv"
                    
                    # Upload to SharePoint
                    sharepoint_client.upload_csv(all_data, filename, columns)
                    logger.info(f"Successfully uploaded data to SharePoint as '{filename}'")
                    print(f"\nSuccessfully uploaded data for {len(all_data)} patients to SharePoint")
                    
                    # Save local backups
                    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
                    
                    if complete_data:
                        complete_filename = f"patients_complete_data_{timestamp}.csv"
                        local_path = os.path.join(OUTPUT_DIRECTORY, complete_filename)
                        sharepoint_client.save_csv_local(complete_data, local_path, columns)
                        logger.info(f"Saved local backup of complete data: {local_path}")
                    
                    if missing_data:
                        missing_filename = f"patients_missing_data_{timestamp}.csv"
                        local_path = os.path.join(OUTPUT_DIRECTORY, missing_filename)
                        sharepoint_client.save_csv_local(missing_data, local_path, columns)
                        logger.info(f"Saved local backup of missing data: {local_path}")
                    
                    # Mark progress as complete
                    progress.complete(f"Successfully processed {len(all_data)} patients")
                    
                except Exception as e:
                    logger.error(f"Error saving data: {e}")
                    print(f"\nError saving data: {e}")
                    
                    # Try to save local backups even if SharePoint fails
                    try:
                        os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
                        
                        all_filename = f"all_patients_data_{timestamp}.csv"
                        local_path = os.path.join(OUTPUT_DIRECTORY, all_filename)
                        sharepoint_client.save_csv_local(all_data, local_path, columns)
                        logger.info(f"Saved local backup of all data: {local_path}")
                        print(f"Saved local backup to {local_path}")
                        
                        # Update progress
                        progress.set_error(f"SharePoint upload failed, but saved local backup: {local_path}")
                        
                    except Exception as backup_error:
                        logger.error(f"Error saving local backup: {backup_error}")
                        progress.set_error(f"Failed to save data: {str(e)}")
            else:
                logger.warning("No patient data to save")
                progress.complete("No patient data to save")
        else:
            logger.warning("No active patients found")
            progress.complete("No active patients found")
        
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