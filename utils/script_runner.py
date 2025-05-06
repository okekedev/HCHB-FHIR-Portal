#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alert Media Integration Script

This script collects alert data from FHIR R4 APIs and prepares notifications 
for the Alert Media system. It processes critical patient alerts that require 
immediate attention from healthcare providers.

Uses shared utilities for:
- FHIR API client with token management
- SharePoint integration
- Standardized logging
- Centralized configuration
"""

import os
import re
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# Import shared utilities
from utils.fhir_client import fhir_client
from utils.sharepoint_client import sharepoint_client
from utils.logging_setup import configure_logging
from utils.progress_tracker import ProgressTracker
from utils.config import (
    BATCH_SIZE, MAX_WORKERS, OUTPUT_DIRECTORY
)

# Configure logging for this script
logger = configure_logging('alert_media_batch')

# Alert media specific configuration
ALERT_FILENAME = "alert_media_data.csv"
ALERT_CATEGORIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

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

def get_critical_conditions():
    """
    Get patients with critical conditions that require alerts.
    
    Returns:
        List of condition resources
    """
    logger.info("Retrieving critical patient conditions...")
    
    # Parameters to search for critical conditions
    params = {
        "severity": "severe",
        "clinical-status": "active",
        "_count": BATCH_SIZE
    }
    
    # Use the FHIR client to get critical conditions
    critical_conditions = fhir_client.get_all_pages("Condition", params)
    
    logger.info(f"Retrieved {len(critical_conditions)} critical conditions")
    return critical_conditions

def get_patient_data_batch(patient_ids, progress_tracker=None):
    """
    Get patient data for a batch of patient IDs.
    
    Args:
        patient_ids: List of patient IDs
        progress_tracker: Optional progress tracker
        
    Returns:
        Dictionary mapping patient IDs to patient data
    """
    logger.info(f"Getting patient data for {len(patient_ids)} patients...")
    
    patient_data = {}
    
    # Create batches for processing
    batches = [patient_ids[i:i+BATCH_SIZE] for i in range(0, len(patient_ids), BATCH_SIZE)]
    
    # Process batches with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_batch = {
            executor.submit(_process_patient_batch, batch): batch 
            for batch in batches
        }
        
        # Process completed tasks
        for i, future in enumerate(future_to_batch):
            try:
                batch_data = future.result()
                patient_data.update(batch_data)
                logger.info(f"Processed patient batch {i+1}/{len(batches)}")
                
                # Update progress if tracker provided
                if progress_tracker:
                    progress_tracker.update(
                        len(patient_data),
                        f"Retrieved data for {len(patient_data)} of {len(patient_ids)} patients"
                    )
            except Exception as e:
                logger.error(f"Error processing patient batch {i+1}: {e}")
    
    return patient_data

def _process_patient_batch(batch_patient_ids):
    """
    Process a batch of patient IDs to get their data.
    
    Args:
        batch_patient_ids: List of patient IDs
        
    Returns:
        Dictionary mapping patient IDs to patient data
    """
    batch_data = {}
    
    # Process each patient
    for patient_id in batch_patient_ids:
        try:
            # Get patient resource
            patient = fhir_client.get_resource("Patient", patient_id)
            
            # Extract patient data
            name = ""
            if "name" in patient and patient["name"]:
                # Get official name or first name
                official_name = next(
                    (n for n in patient["name"] if n.get("use") == "official"), 
                    patient["name"][0] if patient["name"] else None
                )
                
                if official_name:
                    # Format as "Family, Given"
                    family = official_name.get("family", "")
                    given = " ".join(official_name.get("given", []))
                    
                    if family and given:
                        name = f"{family}, {given}"
                    elif family:
                        name = family
                    elif given:
                        name = given
            
            # Get contact information
            phone = ""
            if "telecom" in patient:
                # First try to get home phone
                home_phone = next(
                    (t.get("value") for t in patient["telecom"] 
                     if t.get("system") == "phone" and t.get("use") == "home"),
                    None
                )
                
                if home_phone:
                    phone = normalize_phone_number(home_phone)
                else:
                    # Then try any phone
                    any_phone = next(
                        (t.get("value") for t in patient["telecom"] 
                         if t.get("system") == "phone"),
                        None
                    )
                    if any_phone:
                        phone = normalize_phone_number(any_phone)
            
            # Get address
            address = ""
            if "address" in patient and patient["address"]:
                addr = patient["address"][0]
                
                # Get address components
                street = ", ".join(addr.get("line", []))
                city = addr.get("city", "")
                state = addr.get("state", "")
                zip_code = addr.get("postalCode", "")
                
                # Format address
                address_parts = []
                if street:
                    address_parts.append(street)
                if city:
                    address_parts.append(city)
                if state:
                    address_parts.append(state)
                if zip_code:
                    address_parts.append(zip_code)
                
                address = ", ".join(address_parts)
            
            # Store patient data
            batch_data[patient_id] = {
                "patient_id": patient_id,
                "name": name,
                "phone": phone,
                "address": address,
                "active": patient.get("active", False)
            }
            
        except Exception as e:
            logger.error(f"Error processing patient {patient_id}: {e}")
    
    return batch_data

def get_care_providers(patient_ids, progress_tracker=None):
    """
    Get care providers for patients.
    
    Args:
        patient_ids: List of patient IDs
        progress_tracker: Optional progress tracker
        
    Returns:
        Dictionary mapping patient IDs to care provider info
    """
    logger.info(f"Getting care providers for {len(patient_ids)} patients...")
    
    care_providers = {}
    
    # Create batches for processing
    batches = [patient_ids[i:i+BATCH_SIZE] for i in range(0, len(patient_ids), BATCH_SIZE)]
    
    # Process batches with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_batch = {
            executor.submit(_process_careteam_batch, batch): batch 
            for batch in batches
        }
        
        # Process completed tasks
        for i, future in enumerate(future_to_batch):
            try:
                batch_providers = future.result()
                care_providers.update(batch_providers)
                logger.info(f"Processed care team batch {i+1}/{len(batches)}")
                
                # Update progress if tracker provided
                if progress_tracker:
                    processed_count = len(care_providers)
                    progress_tracker.update(
                        processed_count,
                        f"Retrieved care providers for {processed_count} of {len(patient_ids)} patients"
                    )
            except Exception as e:
                logger.error(f"Error processing care team batch {i+1}: {e}")
    
    return care_providers

def _process_careteam_batch(batch_patient_ids):
    """
    Process a batch of patient IDs to get their care teams.
    
    Args:
        batch_patient_ids: List of patient IDs
        
    Returns:
        Dictionary mapping patient IDs to care provider info
    """
    batch_providers = {}
    
    for patient_id in batch_patient_ids:
        try:
            # Query to get care teams for this patient
            params = {
                "patient": f"Patient/{patient_id}",
                "status": "active",
                "_count": 100
            }
            
            # Get care teams
            care_teams = fhir_client.get_all_pages("CareTeam", params)
            
            # Process care teams to get providers
            providers = []
            
            for care_team in care_teams:
                # Get participants
                if "participant" in care_team:
                    for participant in care_team["participant"]:
                        # Get provider reference
                        if "member" in participant and "reference" in participant["member"]:
                            reference = participant["member"]["reference"]
                            
                            # Check if reference is a practitioner
                            if reference.startswith("Practitioner/"):
                                practitioner_id = reference.replace("Practitioner/", "")
                                
                                # Get role
                                role = ""
                                if "role" in participant:
                                    for role_coding in participant["role"]:
                                        if "coding" in role_coding:
                                            for coding in role_coding["coding"]:
                                                role = coding.get("display", "")
                                                if role:
                                                    break
                                            if role:
                                                break
                                
                                # Get provider details
                                try:
                                    practitioner = fhir_client.get_resource("Practitioner", practitioner_id)
                                    
                                    # Get provider name
                                    name = ""
                                    if "name" in practitioner and practitioner["name"]:
                                        provider_name = practitioner["name"][0]
                                        family = provider_name.get("family", "")
                                        given = " ".join(provider_name.get("given", []))
                                        
                                        if family and given:
                                            name = f"{family}, {given}"
                                        elif family:
                                            name = family
                                        elif given:
                                            name = given
                                    
                                    # Get contact info
                                    contact = ""
                                    if "telecom" in practitioner:
                                        work_phone = next(
                                            (t.get("value") for t in practitioner["telecom"] 
                                             if t.get("system") == "phone" and t.get("use") == "work"),
                                            None
                                        )
                                        
                                        if work_phone:
                                            contact = normalize_phone_number(work_phone)
                                        else:
                                            # Try any phone
                                            any_phone = next(
                                                (t.get("value") for t in practitioner["telecom"] 
                                                 if t.get("system") == "phone"),
                                                None
                                            )
                                            if any_phone:
                                                contact = normalize_phone_number(any_phone)
                                    
                                    # Add provider to list
                                    providers.append({
                                        "id": practitioner_id,
                                        "name": name,
                                        "role": role,
                                        "contact": contact
                                    })
                                    
                                except Exception as e:
                                    logger.error(f"Error getting practitioner {practitioner_id}: {e}")
            
            # Store providers for this patient
            if providers:
                batch_providers[patient_id] = providers
            
        except Exception as e:
            logger.error(f"Error processing care team for patient {patient_id}: {e}")
    
    return batch_providers

def prepare_alert_data(conditions, patient_data, care_providers, progress_tracker=None):
    """
    Prepare alert data for Alert Media system.
    
    Args:
        conditions: List of condition resources
        patient_data: Dictionary mapping patient IDs to patient data
        care_providers: Dictionary mapping patient IDs to care provider info
        progress_tracker: Optional progress tracker
        
    Returns:
        List of prepared alert data records
    """
    logger.info("Preparing alert data...")
    
    alerts = []
    
    # Process each condition
    for i, condition in enumerate(conditions):
        try:
            # Get patient reference
            if "subject" in condition and "reference" in condition["subject"]:
                patient_ref = condition["subject"]["reference"]
                
                if patient_ref.startswith("Patient/"):
                    patient_id = patient_ref.replace("Patient/", "")
                    
                    # Check if we have data for this patient
                    if patient_id in patient_data:
                        patient = patient_data[patient_id]
                        
                        # Get condition details
                        condition_code = ""
                        condition_text = ""
                        
                        if "code" in condition:
                            # Try to get display text
                            if "text" in condition["code"]:
                                condition_text = condition["code"]["text"]
                            
                            # Try to get code
                            if "coding" in condition["code"] and condition["code"]["coding"]:
                                coding = condition["code"]["coding"][0]
                                condition_code = coding.get("code", "")
                                
                                # If no text, use display from coding
                                if not condition_text:
                                    condition_text = coding.get("display", "")
                        
                        # Determine priority based on severity
                        severity = "MEDIUM"  # Default
                        
                        if "severity" in condition:
                            severity_coding = condition["severity"]
                            if "coding" in severity_coding and severity_coding["coding"]:
                                severity_display = severity_coding["coding"][0].get("display", "").upper()
                                
                                if "SEVERE" in severity_display or "CRITICAL" in severity_display:
                                    severity = "CRITICAL"
                                elif "HIGH" in severity_display:
                                    severity = "HIGH"
                                elif "MODERATE" in severity_display:
                                    severity = "MEDIUM"
                                elif "LOW" in severity_display or "MILD" in severity_display:
                                    severity = "LOW"
                        
                        # Get care providers for this patient
                        providers = []
                        if patient_id in care_providers:
                            providers = care_providers[patient_id]
                        
                        # Create alert record
                        alert = {
                            "patient_id": patient_id,
                            "patient_name": patient["name"],
                            "patient_phone": patient["phone"],
                            "patient_address": patient["address"],
                            "condition_code": condition_code,
                            "condition_text": condition_text,
                            "severity": severity,
                            "onset_date": condition.get("onsetDateTime", ""),
                            "recorded_date": condition.get("recordedDate", ""),
                            "providers": ", ".join([p["name"] + " (" + p["role"] + ")" for p in providers]) if providers else "",
                            "provider_contacts": ", ".join([p["contact"] for p in providers if p["contact"]]) if providers else "",
                            "alert_timestamp": datetime.now().isoformat()
                        }
                        
                        alerts.append(alert)
            
            # Update progress if tracker provided
            if progress_tracker and (i % 10 == 0 or i == len(conditions) - 1):
                progress_tracker.update(
                    i + 1,
                    f"Prepared {i+1} of {len(conditions)} alerts"
                )
                        
        except Exception as e:
            logger.error(f"Error preparing alert for condition: {e}")
    
    logger.info(f"Prepared {len(alerts)} alerts")
    return alerts

def save_alerts_locally(alerts):
    """
    Save alerts to a local CSV file for backup.
    
    Args:
        alerts: List of alert records
        
    Returns:
        Path to saved file
    """
    if not alerts:
        logger.warning("No alerts to save locally")
        return None
    
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIRECTORY):
        os.makedirs(OUTPUT_DIRECTORY)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"alert_media_data_{timestamp}.csv"
    output_path = os.path.join(OUTPUT_DIRECTORY, filename)
    
    # Define columns for CSV
    columns = [
        "patient_id", "patient_name", "patient_phone", "patient_address",
        "condition_code", "condition_text", "severity", "onset_date",
        "recorded_date", "providers", "provider_contacts", "alert_timestamp"
    ]
    
    # Save to CSV
    import csv
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(alerts)
    
    logger.info(f"Saved {len(alerts)} alerts to {output_path}")
    return output_path

def main():
    """Main function to run the script"""
    try:
        # Record start time for performance tracking
        start_time = datetime.now()
        logger.info(f"Script started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Initialize progress tracker
        progress = ProgressTracker("Alert Media Processing")
        
        # Step 1: Get critical conditions
        progress.update(0, "Retrieving critical conditions")
        conditions = get_critical_conditions()
        
        if conditions:
            # Update total items now that we know it
            progress.total_items = len(conditions)
            progress.update(0, f"Found {len(conditions)} critical conditions")
            
            # Step 2: Get patient IDs from conditions
            patient_ids = []
            for condition in conditions:
                if "subject" in condition and "reference" in condition["subject"]:
                    patient_ref = condition["subject"]["reference"]
                    if patient_ref.startswith("Patient/"):
                        patient_id = patient_ref.replace("Patient/", "")
                        patient_ids.append(patient_id)
            
            # Remove duplicates
            patient_ids = list(set(patient_ids))
            logger.info(f"Found {len(patient_ids)} unique patients with critical conditions")
            progress.update(conditions.index(conditions[0]) if conditions else 0, 
                          f"Processing {len(patient_ids)} unique patients")
            
            # Step 3: Get patient data
            progress.update(int(len(conditions) * 0.1), "Retrieving patient demographic data")
            patient_data = get_patient_data_batch(patient_ids, progress_tracker=progress)
            
            # Step 4: Get care providers
            progress.update(int(len(conditions) * 0.4), "Retrieving care provider information")
            care_providers = get_care_providers(patient_ids, progress_tracker=progress)
            
            # Step 5: Prepare alert data
            progress.update(int(len(conditions) * 0.7), "Preparing alerts")
            alerts = prepare_alert_data(conditions, patient_data, care_providers, progress_tracker=progress)
            
            if alerts:
                # Step 6: Save alerts locally for backup
                progress.update(int(len(conditions) * 0.9), "Saving alerts locally")
                save_alerts_locally(alerts)
                
                # Step 7: Upload to SharePoint
                try:
                    progress.update(int(len(conditions) * 0.95), "Uploading to SharePoint")
                    
                    # Define fieldnames for CSV
                    fieldnames = [
                        "patient_id", "patient_name", "patient_phone", "patient_address",
                        "condition_code", "condition_text", "severity", "onset_date",
                        "recorded_date", "providers", "provider_contacts", "alert_timestamp"
                    ]
                    
                    # Upload to SharePoint
                    sharepoint_client.upload_csv(alerts, ALERT_FILENAME, fieldnames)
                    logger.info(f"Successfully uploaded {len(alerts)} alerts to SharePoint as '{ALERT_FILENAME}'")
                    print(f"\nSuccessfully uploaded {len(alerts)} alerts to SharePoint as '{ALERT_FILENAME}'")
                    
                    # Mark progress as complete
                    progress.complete(f"Processed {len(alerts)} alerts successfully")
                
                except Exception as e:
                    logger.error(f"Error uploading to SharePoint: {e}")
                    print(f"\nError uploading to SharePoint: {e}")
                    progress.set_error(f"Error uploading to SharePoint: {str(e)}")
            else:
                logger.info("No alerts to process")
                print("\nNo alerts to process")
                progress.complete("No alerts to process")
        else:
            logger.info("No critical conditions found")
            print("\nNo critical conditions found")
            progress.complete("No critical conditions found")
        
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