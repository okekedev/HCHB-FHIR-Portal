"""
FHIR Patient Data Collector Script

This script efficiently collects patient data from FHIR R4 APIs and exports it to SharePoint.
Fields collected: LastName, FirstName, MI, Street, City, State, Zip, County, Phone

Uses shared utilities for:
- FHIR API client with token management
- SharePoint integration
- Standardized logging
- Centralized configuration
"""

import re
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Import shared utilities
from utils.fhir_client import fhir_client
from utils.sharepoint_client import sharepoint_client
from utils.logging_setup import configure_logging
from utils.progress_tracker import ProgressTracker  # Add this import
from utils.config import (
    BATCH_SIZE, MAX_WORKERS, OUTPUT_DIRECTORY, 
    PATIENT_DATA_FILENAME
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

def get_all_active_patients(batch_size=1000, progress_tracker=None):
    """
    Get all active patients using pagination.
    
    Args:
        batch_size: Number of patients to fetch per page
        progress_tracker: Optional progress tracker
        
    Returns:
        List of patient resources with birthdate
    """
    logger.info("Starting retrieval of all active patients...")
    
    # Update progress if tracker provided
    if progress_tracker:
        progress_tracker.update(0, "Retrieving active patients from FHIR API")
    
    # Parameters for the search - requesting more patient details directly
    params = {
        "active": "true",              # Only get active patients
        "_count": batch_size,          # Number of patients per page
        "_elements": "id,name,birthDate,address,telecom"  # Request specific elements
    }
    
    # Use the FHIR client to get all pages of patients
    all_patients = fhir_client.get_all_pages("Patient", params)
    
    # Filter out patients without birthdate
    patients_with_birthdate = []
    patients_without_birthdate = 0
    
    for patient in all_patients:
        if "birthDate" in patient and patient["birthDate"]:
            patients_with_birthdate.append(patient)
        else:
            patients_without_birthdate += 1
    
    logger.info(f"Completed retrieval of active patients:")
    logger.info(f"  - {len(patients_with_birthdate)} active patients with birthdate")
    logger.info(f"  - {patients_without_birthdate} patients without birthdate (filtered out)")
    
    # Update progress if tracker provided
    if progress_tracker:
        progress_tracker.update(
            progress_tracker.processed_items + 1,
            f"Retrieved {len(patients_with_birthdate)} active patients with birthdate"
        )
    
    return patients_with_birthdate

def process_patients_batch(patients_batch, batch_index, total_batches, progress_tracker=None):
    """
    Process a batch of patients in parallel.
    
    Args:
        patients_batch: List of patient resources to process
        batch_index: Current batch index (1-based)
        total_batches: Total number of batches
        progress_tracker: Optional progress tracker
        
    Returns:
        List of processed patient data dictionaries
    """
    logger.info(f"Processing batch {batch_index}/{total_batches} with {len(patients_batch)} patients...")
    
    # Update progress if tracker provided
    if progress_tracker:
        progress_percentage = (batch_index / total_batches) * 100
        progress_tracker.update(
            int(progress_tracker.total_items * (batch_index / total_batches)),
            f"Processing batch {batch_index}/{total_batches} ({len(patients_batch)} patients)"
        )
    
    processed_data = []
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Process each patient concurrently
        future_to_patient = {
            executor.submit(process_patient, patient): patient 
            for patient in patients_batch
        }
        
        # Collect results as they complete
        for future in future_to_patient:
            try:
                patient_data = future.result()
                if patient_data:
                    processed_data.append(patient_data)
            except Exception as e:
                logger.error(f"Error processing patient: {e}")
    
    logger.info(f"Processed {len(processed_data)} patients in batch {batch_index}/{total_batches}")
    
    # Small increment for completing this batch
    if progress_tracker:
        current_count = int(progress_tracker.total_items * (batch_index / total_batches))
        progress_tracker.update(
            current_count,
            f"Completed batch {batch_index}/{total_batches} - {current_count} of {progress_tracker.total_items} patients"
        )
    
    return processed_data

def process_patient(patient):
    """
    Process a single patient resource to extract relevant data.
    
    Args:
        patient: Patient resource from FHIR API
        
    Returns:
        Dictionary with extracted patient data
    """
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
    county = ""
    
    if "address" in patient and patient["address"]:
        address = patient["address"][0]
        
        # Street (first line of address)
        if "line" in address and address["line"]:
            street = address["line"][0]
        
        city = address.get("city", "")
        state = address.get("state", "")
        zip_code = address.get("postalCode", "")
        
        # Extract county directly from address if available
        county = address.get("district", "")
    
    # Extract phone number
    phone = ""
    if "telecom" in patient:
        # First prioritize home phone
        for telecom in patient["telecom"]:
            if telecom.get("system") == "phone" and telecom.get("use") == "home":
                phone = normalize_phone_number(telecom.get("value", ""))
                break
        
        # If no home phone, try any phone
        if not phone:
            for telecom in patient["telecom"]:
                if telecom.get("system") == "phone":
                    phone = normalize_phone_number(telecom.get("value", ""))
                    break
    
    # Create patient data dictionary
    patient_data = {
        "patientId": patient_id,
        "lastName": last_name,
        "firstName": first_name,
        "mi": middle_initial,
        "street": street,
        "city": city,
        "state": state,
        "zip": zip_code,
        "county": county,
        "phone": phone
    }
    
    return patient_data

def save_to_local_csv(data_list, filename):
    """
    Save patient data to a local CSV file for backup.
    
    Args:
        data_list: List of patient data dictionaries
        filename: Output filename
        
    Returns:
        Output filename or None if no data to save
    """
    if not data_list:
        logger.warning(f"No patient data to save to {filename}")
        return None
    
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIRECTORY):
        os.makedirs(OUTPUT_DIRECTORY)
    
    # Full path to the output file
    output_filename = os.path.join(OUTPUT_DIRECTORY, filename)
    
    # Define columns for the CSV
    fieldnames = [
        "patientId", "lastName", "firstName", "mi", "street", 
        "city", "state", "zip", "county", "phone"
    ]
    
    # Write to CSV with proper formatting
    import csv
    with open(output_filename, 'w', newline='') as file:
        writer = csv.DictWriter(
            file, 
            fieldnames=fieldnames,
            quoting=csv.QUOTE_MINIMAL,      # Use quotes only when needed
            lineterminator='\r\n'           # Windows-style line endings for compatibility
        )
        writer.writeheader()
        writer.writerows(data_list)
    
    logger.info(f"Saved {len(data_list)} patients to local file: {output_filename}")
    return output_filename

def main():
    """Main function to run the script"""
    try:
        # Record start time for performance tracking
        start_time = datetime.now()
        logger.info(f"Script started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Initialize progress tracker
        progress = ProgressTracker("Patient Demographics")
        
        # Step 1: Get all active patients with birthdate
        progress.update(0, "Retrieving patient data from FHIR API")
        all_patients = get_all_active_patients(batch_size=BATCH_SIZE, progress_tracker=progress)
        
        if all_patients:
            # Update total items now that we know the count
            progress.total_items = len(all_patients)
            progress.update(1, f"Processing {len(all_patients)} patients")
            
            # Step 2: Process patients in batches using ThreadPoolExecutor
            processed_patients = []
            
            # Create batches for parallel processing
            batch_size = 200  # Smaller batch size for parallel processing
            batches = [all_patients[i:i+batch_size] for i in range(0, len(all_patients), batch_size)]
            
            logger.info(f"Processing {len(all_patients)} patients in {len(batches)} batches...")
            
            # Process each batch
            for i, batch in enumerate(batches):
                logger.info(f"Processing batch {i+1}/{len(batches)}...")
                batch_data = process_patients_batch(batch, i+1, len(batches), progress_tracker=progress)
                processed_patients.extend(batch_data)
                logger.info(f"Completed batch {i+1}/{len(batches)}")
            
            # Step 3: Create backup and upload to SharePoint
            if processed_patients:
                # Update progress
                progress.update(
                    int(progress.total_items * 0.9),
                    f"Saving {len(processed_patients)} processed patient records"
                )
                
                # Create backup with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"patient_data_backup_{timestamp}.csv"
                save_to_local_csv(processed_patients, backup_filename)
                
                # Upload to SharePoint
                try:
                    progress.update(
                        int(progress.total_items * 0.95),
                        f"Uploading {len(processed_patients)} patient records to SharePoint"
                    )
                    
                    # Define fieldnames for CSV
                    fieldnames = [
                        "patientId", "lastName", "firstName", "mi", "street", 
                        "city", "state", "zip", "county", "phone"
                    ]
                    
                    # Upload to SharePoint
                    sharepoint_client.upload_csv(processed_patients, PATIENT_DATA_FILENAME, fieldnames)
                    logger.info(f"Successfully uploaded {len(processed_patients)} patient records to SharePoint")
                    print(f"\nSuccessfully uploaded {len(processed_patients)} patient records to SharePoint as '{PATIENT_DATA_FILENAME}'")
                    
                    # Mark progress as complete
                    progress.complete(f"Successfully processed {len(processed_patients)} patient records")
                
                except Exception as e:
                    logger.error(f"Error uploading to SharePoint: {e}")
                    print(f"\nError uploading to SharePoint: {e}")
                    print(f"\nPatient data was saved locally to {backup_filename}")
                    
                    # Update progress with error
                    progress.set_error(f"SharePoint upload failed: {str(e)}")
                    return False
            else:
                logger.warning("No patient data to upload")
                print("\nNo patient data to upload")
                progress.complete("No patient data to upload")
        else:
            logger.warning("No active patients found")
            print("\nNo active patients found")
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