"""
Coordination Notes Script

This script retrieves coordination notes from the HCHB FHIR API, which contain
important information about care coordination activities, interdisciplinary team
communications, and patient care planning notes.

Uses shared utilities for:
- FHIR API client with token management
- SharePoint integration
- Standardized logging
- Centralized configuration
"""

import base64
import time
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential

# Import shared utilities
from utils.fhir_client import fhir_client
from utils.sharepoint_client import sharepoint_client
from utils.logging_setup import configure_logging
from utils.config import (
    API_BASE_URL, REQUEST_TIMEOUT, COORDINATION_NOTES_FILENAME
)

# Configure logging
logger = configure_logging('coordination_notes_csv')

# Coordination notes specific configuration
SYNC_BUFFER_MINUTES = 30
MAX_PAGES_PER_REQUEST = 1000  # Max pages before advancing date window
PAGE_SIZE = 100  # Keep smaller to avoid limits

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_page(url, params=None):
    """
    Fetch a page of coordination notes with retry logic.
    
    Args:
        url: API URL to fetch
        params: Query parameters (optional)
        
    Returns:
        Response JSON data
    """
    # Use the FHIR client to make the request
    if params:
        return fhir_client.make_request(url, params=params)
    else:
        return fhir_client.make_request(url)

def get_last_fetch_date():
    """
    Retrieve last fetch date from SharePoint CSV with buffer.
    
    Returns:
        ISO formatted date string for the last fetch date
    """
    logger.info("Retrieving last fetch date from coordination notes file")
    
    try:
        # Download existing notes from SharePoint
        existing_notes = sharepoint_client.download_csv(COORDINATION_NOTES_FILENAME)
        
        if existing_notes:
            # Find the most recent API run date
            latest_date = None
            for row in existing_notes:
                if "Api_Run_Date" in row and row["Api_Run_Date"]:
                    try:
                        dt = datetime.fromisoformat(row["Api_Run_Date"].replace("Z", "+00:00"))
                        if not latest_date or dt > latest_date:
                            latest_date = dt
                    except ValueError:
                        continue
            
            # Apply buffer to avoid duplicate notes
            if latest_date:
                latest_date = latest_date - timedelta(minutes=SYNC_BUFFER_MINUTES)
                logger.info(f"Found last fetch date: {latest_date.isoformat()}")
                return latest_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    except Exception as e:
        logger.error(f"Failed to read last fetch date: {e}")
    
    # Default to 60 days ago if no valid date found
    default_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.info(f"Using default fetch date: {default_date}")
    return default_date

def fetch_notes_by_date_range(start_date, end_date=None):
    """
    Fetch coordination notes within a specified date range.
    
    Args:
        start_date: Start date in ISO format
        end_date: End date in ISO format (optional, defaults to now)
        
    Returns:
        Tuple of (list of note records, latest date found)
    """
    logger.info(f"Fetching notes between {start_date} and {end_date if end_date else 'now'}")
    
    page_number = 1
    batch_notes = []
    
    # Build parameters for the search
    params = {
        "category": "coordination-note",
        "status": "current",
        "_count": PAGE_SIZE
    }
    
    # Add date filter
    if end_date:
        params["date"] = f"ge{start_date}&date=lt{end_date}"
    else:
        params["date"] = f"ge{start_date}"
    
    # Start with the Document Reference endpoint
    url = "DocumentReference"
    continue_fetching = True
    batch_latest_date = start_date
    
    # Track the run timestamp for consistent dating
    run_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    while continue_fetching and page_number <= MAX_PAGES_PER_REQUEST:
        try:
            # Fetch the current page
            data = fetch_page(url, params if page_number == 1 else None)
            
            # Process the entries
            entries = data.get("entry", [])
            for entry in entries:
                resource = entry.get("resource", {})
                resource_date = resource.get("date", "")
                patient_id = resource.get("subject", {}).get("reference", "").replace("Patient/", "")
                note_type = resource.get("type", {}).get("text", "")
                worker_id = resource.get("author", [{}])[0].get("reference", "").replace("Practitioner/", "")
                
                # Extract note content (base64 encoded)
                content = resource.get("content", [{}])[0]
                attachment = content.get("attachment", {})
                
                # Decode the note content
                try:
                    decoded_note = base64.b64decode(attachment.get("data", "")).decode("utf-8") if attachment.get("data") else ""
                except Exception as e:
                    logger.error(f"Failed to decode base64 data for resource {resource.get('id', '')}: {e}")
                    decoded_note = ""
                
                # Create the note record
                note_record = {
                    "Patient_ID": patient_id,
                    "Note_Date": resource_date,
                    "Note_Type": note_type,
                    "Worker_ID": worker_id,
                    "Note_Status": resource.get("status", ""),
                    "Last_Update": resource.get("meta", {}).get("lastUpdated", ""),
                    "Last_Updated_By": "",
                    "Note": decoded_note,
                    "Episode_ID": resource.get("context", {}).get("encounter", [{}])[0].get("reference", "").split("/")[-1] if resource.get("context", {}).get("encounter") else "",
                    "Api_Run_Date": run_timestamp
                }
                batch_notes.append(note_record)
                
                # Track the latest date found
                if resource_date and resource_date > batch_latest_date:
                    batch_latest_date = resource_date
            
            logger.info(f"Page {page_number}: Retrieved {len(entries)} notes")
            
            # Check for next page link
            next_link = next((link.get("url") for link in data.get("link", []) if link.get("relation") == "next"), None)
            if next_link:
                # Extract the path from the full URL
                if next_link.startswith(API_BASE_URL):
                    url = next_link[len(API_BASE_URL)+1:]  # +1 for the trailing slash
                else:
                    url = next_link
                page_number += 1
                params = None
            else:
                continue_fetching = False
                
        except Exception as e:
            logger.error(f"Failed to fetch page {page_number}: {e}")
            break
    
    return batch_notes, batch_latest_date

def main():
    """Main function to fetch and upload coordination notes."""
    try:
        logger.info("Starting coordination notes processing...")

        # Step 1: Get last fetch date
        last_fetch_date = get_last_fetch_date()
        logger.info(f"Fetching notes since {last_fetch_date}")

        # Step 2: Fetch coordination notes
        coordination_notes = []
        current_date = last_fetch_date
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        more_data = True

        # Fetch notes in batches until no more data or we reach current time
        while more_data:
            batch_notes, batch_latest_date = fetch_notes_by_date_range(current_date)
            
            if not batch_notes:
                logger.info(f"No more entries to fetch after {current_date}")
                more_data = False
                break
            
            coordination_notes.extend(batch_notes)
            logger.info(f"Processed {len(batch_notes)} notes, total so far: {len(coordination_notes)}")
            
            # Advance date window
            try:
                # Handle various date formats
                date_format = "%Y-%m-%dT%H:%M:%S"
                if "." in batch_latest_date:
                    date_format += ".%f"
                if "Z" in batch_latest_date:
                    date_format += "Z"
                elif "+" in batch_latest_date:
                    date_format += "%z"
                
                # Clean up the date string
                clean_date = batch_latest_date
                if "+" in clean_date:
                    clean_date = clean_date.split("+")[0]
                if "Z" in clean_date:
                    clean_date = clean_date.replace("Z", "")
                
                # Parse and advance by 1 second
                parsed_date = datetime.strptime(clean_date, date_format.replace("Z", "").replace("%z", ""))
                next_date = (parsed_date + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
                current_date = next_date
                logger.info(f"Moving date window to {current_date}")
            except Exception as e:
                logger.error(f"Error parsing date {batch_latest_date}: {e}")
                current_date = batch_latest_date + "0"  # Fallback approach
                logger.info(f"Using fallback date {current_date}")
            
            # Stop if we've reached the current time
            if current_date >= now:
                logger.info("Reached current time, finished fetching")
                more_data = False

        # Step 3: Check if we found any new notes
        if not coordination_notes:
            logger.info("No new coordination notes found.")
            print("\nNo new coordination notes found.")
            return True

        # Step 4: Download existing notes
        existing_notes = sharepoint_client.download_csv(COORDINATION_NOTES_FILENAME)
        logger.info(f"Downloaded {len(existing_notes)} existing notes from SharePoint")
        
        # Step 5: Define fieldnames for CSV
        fieldnames = [
            "Patient_ID", "Note_Date", "Note_Type", "Worker_ID",
            "Note_Status", "Last_Update", "Last_Updated_By", "Note", "Episode_ID", "Api_Run_Date"
        ]
        
        # Step 6: Upload concatenated notes to SharePoint
        try:
            # Append new notes to existing notes
            all_notes = existing_notes + coordination_notes
            
            # Upload the combined data
            sharepoint_client.upload_csv(all_notes, COORDINATION_NOTES_FILENAME, fieldnames)
            logger.info(f"Successfully uploaded {len(all_notes)} coordination notes to SharePoint")
            print(f"\nSuccessfully uploaded {len(coordination_notes)} new coordination notes to SharePoint")
            
        except Exception as e:
            logger.error(f"Failed to upload to SharePoint: {e}")
            print(f"\nError uploading to SharePoint: {e}")
            return False
        
        logger.info("Script executed successfully!")
        return True

    except Exception as e:
        logger.error(f"Failed to process coordination notes: {e}")
        print(f"\nError processing coordination notes: {e}")
        return False

if __name__ == "__main__":
    main()