"""
FHIR Worker List Script

This script retrieves workers/practitioners from specific branches (HH WICHITA FALLS or TEMPLATE BRANCH)
from the HCHB FHIR API and exports the data to SharePoint as worker_data.csv.

Uses shared utilities for:
- FHIR API client with token management
- SharePoint integration
- Standardized logging
- Centralized configuration
"""

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Import shared utilities
from utils.fhir_client import fhir_client
from utils.sharepoint_client import sharepoint_client
from utils.logging_setup import configure_logging
from utils.progress_tracker import ProgressTracker  # Add this import
from utils.config import (
    MAX_WORKERS, WORKERS_FILENAME
)

# Configure logging
logger = configure_logging('workers_csv')

# Filter for specific branches
TARGET_BRANCHES = ["HH WICHITA FALLS", "TEMPLATE BRANCH"]

def get_practitioners_with_specific_branches(progress_tracker=None):
    """
    Get practitioners from specific branches
    
    Args:
        progress_tracker: Optional progress tracker
        
    Returns:
        List of practitioner resources in target branches
    """
    logger.info(f"Fetching practitioners from specific branches: {', '.join(TARGET_BRANCHES)}")
    
    if progress_tracker:
        progress_tracker.update(0, f"Fetching practitioners from specific branches: {', '.join(TARGET_BRANCHES)}")
    
    # Parameters - request more practitioners per page
    params = {
        "_count": 200,
        "active": "true,false",
        "_elements": "id,identifier,name,telecom,extension,active,address"
    }
    
    # Use the FHIR client to get all practitioners
    all_practitioners = fhir_client.get_all_pages("Practitioner", params)
    logger.info(f"Retrieved {len(all_practitioners)} practitioners total")
    
    if progress_tracker:
        progress_tracker.update(
            1,
            f"Filtering {len(all_practitioners)} practitioners by branch"
        )
    
    # Filter practitioners
    practitioners_with_branch = []
    practitioners_processed = 0
    
    # Process practitioners to find those in target branches
    for resource in all_practitioners:
        practitioners_processed += 1
        
        # Update progress periodically
        if progress_tracker and practitioners_processed % 50 == 0:
            progress_tracker.update(
                practitioners_processed,
                f"Processed {practitioners_processed} of {len(all_practitioners)} practitioners"
            )
        
        # Check if this is a practitioner-worker
        is_worker = False
        if "identifier" in resource:
            for identifier in resource["identifier"]:
                # Look for the practitioner-worker identifier
                if (identifier.get("use") == "secondary" and 
                    "type" in identifier and 
                    identifier["type"].get("text") == "referenceTable" and
                    identifier.get("value") == "practitioner-worker"):
                    is_worker = True
                    break
        
        # Only include this practitioner if they're a worker
        if not is_worker:
            continue
        
        # Check if practitioner has a branch based on exact HCHB structure
        branch_name = ""
        
        if "extension" in resource:
            # First, look for the practitioner-details extension
            for extension in resource["extension"]:
                # Check for the parent practitioner-details extension
                if extension.get("url") == "https://api.hchb.com/fhir/r4/StructureDefinition/practitioner-details":
                    # Check if it contains nested extensions
                    if "extension" in extension:
                        for nested_ext in extension["extension"]:
                            # Look for the HomeBranch extension
                            if nested_ext.get("url") == "HomeBranch" and "valueReference" in nested_ext:
                                if "display" in nested_ext["valueReference"]:
                                    branch_name = nested_ext["valueReference"]["display"]
                                    if branch_name in TARGET_BRANCHES:
                                        practitioners_with_branch.append(resource)
                                        logger.info(f"Found worker in target branch: {branch_name}")
                                        break
                # Also look for direct HomeBranch extension
                elif extension.get("url") == "HomeBranch" and "valueReference" in extension:
                    if "display" in extension["valueReference"]:
                        branch_name = extension["valueReference"]["display"]
                        if branch_name in TARGET_BRANCHES:
                            practitioners_with_branch.append(resource)
                            logger.info(f"Found worker in target branch: {branch_name}")
                            break
    
    filtered_count = len(practitioners_with_branch)
    logger.info(f"Found {filtered_count} workers in target branches: {', '.join(TARGET_BRANCHES)}")
    
    if progress_tracker:
        progress_tracker.update(
            len(all_practitioners),
            f"Found {filtered_count} workers in target branches"
        )
    
    # Check for duplicates and remove them
    unique_practitioners = []
    seen_ids = set()
    
    for practitioner in practitioners_with_branch:
        practitioner_id = practitioner.get("id")
        if practitioner_id not in seen_ids:
            seen_ids.add(practitioner_id)
            unique_practitioners.append(practitioner)
    
    if len(unique_practitioners) < len(practitioners_with_branch):
        logger.info(f"Removed {len(practitioners_with_branch) - len(unique_practitioners)} duplicate practitioners")
        
        if progress_tracker:
            progress_tracker.update(
                len(all_practitioners),
                f"Removed {len(practitioners_with_branch) - len(unique_practitioners)} duplicates"
            )
    
    return unique_practitioners

def extract_worker_data(worker):
    """Extract relevant worker data including address information"""
    worker_id = worker.get("id", "")
    
    # Extract name
    name = ""
    if "name" in worker and worker["name"]:
        name_obj = worker["name"][0]  # Get the first name entry
        
        given = " ".join(name_obj.get("given", []))
        family = name_obj.get("family", "")
        
        name_parts = []
        if given:
            name_parts.append(given)
        if family:
            name_parts.append(family)
        
        name = " ".join(name_parts)
    
    # Extract branch information based on exact HCHB structure
    branch_name = ""
    branch_id = ""
    if "extension" in worker:
        # First look for the practitioner-details extension
        for extension in worker["extension"]:
            if extension.get("url") == "https://api.hchb.com/fhir/r4/StructureDefinition/practitioner-details":
                # Check if it contains nested extensions
                if "extension" in extension:
                    for nested_ext in extension["extension"]:
                        # Look for the HomeBranch extension
                        if nested_ext.get("url") == "HomeBranch" and "valueReference" in nested_ext:
                            value_ref = nested_ext["valueReference"]
                            if "reference" in value_ref:
                                ref = value_ref["reference"]
                                # Extract the ID from Organization/{id}
                                if ref.startswith("Organization/"):
                                    branch_id = ref.replace("Organization/", "")
                            if "display" in value_ref:
                                branch_name = value_ref["display"]
            
            # Also check for direct HomeBranch extension
            elif extension.get("url") == "HomeBranch" and "valueReference" in extension:
                value_ref = extension["valueReference"]
                if "reference" in value_ref:
                    ref = value_ref["reference"]
                    # Extract the ID from Organization/{id}
                    if ref.startswith("Organization/"):
                        branch_id = ref.replace("Organization/", "")
                if "display" in value_ref:
                    branch_name = value_ref["display"]
    
    # Extract contact information
    contact_info = {}
    if "telecom" in worker:
        for telecom in worker["telecom"]:
            system = telecom.get("system", "")
            value = telecom.get("value", "")
            if system and value:
                contact_info[system] = value
    
    # Extract address information
    address_line = ""
    city = ""
    state = ""
    postal_code = ""
    country = ""
    
    if "address" in worker and worker["address"]:
        # Get the first address
        address = worker["address"][0]
        
        # Extract address components
        if "line" in address and address["line"]:
            address_line = ", ".join(address["line"])
        if "city" in address:
            city = address["city"]
        if "state" in address:
            state = address["state"]
        if "postalCode" in address:
            postal_code = address["postalCode"]
        if "country" in address:
            country = address["country"]
    
    # Active status
    active = "Yes" if worker.get("active", False) else "No"
    
    return {
        "id": worker_id,
        "name": name,
        "branch": branch_name,
        "branch_id": branch_id,
        "phone": contact_info.get("phone", ""),
        "email": contact_info.get("email", ""),
        "address_line": address_line,
        "city": city,
        "state": state,
        "postal_code": postal_code,
        "country": country,
        "active": active
    }

def process_workers(workers, progress_tracker=None):
    """
    Process workers to extract relevant data
    
    Args:
        workers: List of worker resources to process
        progress_tracker: Optional progress tracker
        
    Returns:
        List of processed worker data dictionaries
    """
    logger.info(f"Processing {len(workers)} workers with {MAX_WORKERS} workers...")
    
    if progress_tracker:
        progress_tracker.update(
            progress_tracker.processed_items,
            f"Processing {len(workers)} workers"
        )
    
    processed_workers = []
    
    # Process in batches to provide progress updates
    batch_size = max(5, len(workers) // 10)  # Process in roughly 10 batches for updates
    for i in range(0, len(workers), batch_size):
        batch = workers[i:i+batch_size]
        
        # Process this batch with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Map the extract_worker_data function to the batch
            batch_results = list(executor.map(extract_worker_data, batch))
            processed_workers.extend(batch_results)
        
        # Update progress
        if progress_tracker:
            processed_count = len(processed_workers)
            progress_tracker.update(
                progress_tracker.processed_items,
                f"Processed {processed_count} of {len(workers)} workers"
            )
    
    logger.info(f"Successfully processed {len(processed_workers)} workers")
    return processed_workers

def main():
    try:
        # Record start time
        start_time = datetime.now()
        logger.info(f"Script started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Initialize progress tracker
        progress = ProgressTracker("Workers Directory")
        progress.update(0, "Starting worker data extraction")
        
        # Get workers with branch info directly from Practitioner API
        workers_with_branch = get_practitioners_with_specific_branches(progress_tracker=progress)
        
        # Process and save the worker data to SharePoint
        if workers_with_branch:
            # Update total items now that we know it
            progress.total_items = len(workers_with_branch) * 2  # Processing + upload
            
            # Process worker data
            processed_workers = process_workers(workers_with_branch, progress_tracker=progress)
            
            # Upload to SharePoint
            if processed_workers:
                try:
                    # Update progress
                    progress.update(
                        len(workers_with_branch),
                        f"Uploading {len(processed_workers)} workers to SharePoint"
                    )
                    
                    # Define fieldnames for CSV
                    fieldnames = [
                        "id", 
                        "name", 
                        "branch", 
                        "branch_id", 
                        "phone", 
                        "email", 
                        "address_line", 
                        "city", 
                        "state", 
                        "postal_code", 
                        "country", 
                        "active"
                    ]
                    
                    # Upload to SharePoint
                    sharepoint_client.upload_csv(processed_workers, WORKERS_FILENAME, fieldnames)
                    logger.info(f"Successfully uploaded {len(processed_workers)} workers to SharePoint as '{WORKERS_FILENAME}'")
                    print(f"\nSuccessfully uploaded {len(processed_workers)} workers to SharePoint as '{WORKERS_FILENAME}'")
                    
                    # Mark progress as complete
                    progress.complete(f"Successfully uploaded {len(processed_workers)} workers to SharePoint")
                
                except Exception as e:
                    logger.error(f"SharePoint upload failed: {e}")
                    print(f"\nError uploading to SharePoint: {e}")
                    
                    # Update progress with error
                    progress.set_error(f"SharePoint upload failed: {str(e)}")
                    return False
            else:
                logger.warning("No processed worker data to upload")
                print("\nNo processed worker data to upload")
                progress.complete("No processed worker data to upload")
        else:
            logger.warning("No workers with branch information found")
            print("\nNo workers with branch information found")
            progress.complete("No workers with branch information found")
        
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
        print(f"Error: {e}")
        
        # Update progress with error if progress tracker exists
        if 'progress' in locals():
            progress.set_error(str(e))
            
        return False

if __name__ == "__main__":
    main()