"""
SharePoint client utility for Healing Hands automation scripts.
Handles authentication and file operations with SharePoint.
"""
import requests
import logging
import io
import csv
from datetime import datetime

# Import configuration
from utils.config import (
    SP_CLIENT_ID, SP_CLIENT_SECRET, SP_TENANT_ID, SP_SITE_NAME,
    SP_FOLDER_PATH, REQUEST_TIMEOUT
)

logger = logging.getLogger(__name__)

class SharePointClient:
    """Client for interacting with SharePoint through Microsoft Graph API"""
    
    def __init__(self):
        """Initialize the SharePoint client"""
        self.token = None
        self.site_id = None
        self.drive_id = None
    
    def get_token(self):
        """Get Microsoft Graph API token"""
        if self.token:
            return self.token
            
        url = f"https://login.microsoftonline.com/{SP_TENANT_ID}/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": SP_CLIENT_ID,
            "client_secret": SP_CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
        }
        
        try:
            response = requests.post(url, data=data, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            self.token = response.json()["access_token"]
            logger.info("Successfully obtained Microsoft Graph API token")
            return self.token
        except Exception as e:
            logger.error(f"Failed to obtain Microsoft Graph API token: {e}")
            raise
    
    def get_headers(self):
        """Get authentication headers with current token"""
        token = self.get_token()
        return {
            "Authorization": f"Bearer {token}"
        }
    
    def get_site_id(self):
        """Get the SharePoint site ID"""
        if self.site_id:
            return self.site_id
            
        site_url = f"https://graph.microsoft.com/v1.0/sites/hhhdomain.sharepoint.com:/sites/{SP_SITE_NAME}"
        headers = self.get_headers()
        
        try:
            response = requests.get(site_url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            self.site_id = response.json()["id"]
            logger.info(f"Retrieved site ID for {SP_SITE_NAME}")
            return self.site_id
        except Exception as e:
            logger.error(f"Failed to retrieve site ID: {e}")
            raise
    
    def get_drive_id(self):
        """Get the default document library drive ID"""
        if self.drive_id:
            return self.drive_id
            
        site_id = self.get_site_id()
        drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        headers = self.get_headers()
        
        try:
            response = requests.get(drives_url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            drives = response.json()["value"]
            
            if not drives:
                raise ValueError("No document libraries found in SharePoint site")
            
            self.drive_id = drives[0]["id"]
            logger.info(f"Retrieved drive ID")
            return self.drive_id
        except Exception as e:
            logger.error(f"Failed to retrieve drive ID: {e}")
            raise
    
    def ensure_folder_exists(self):
        """Ensure the target folder exists, create if not"""
        site_id = self.get_site_id()
        drive_id = self.get_drive_id()
        headers = self.get_headers()
        
        folder_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{SP_FOLDER_PATH}"
        
        try:
            folder_response = requests.get(folder_url, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if folder_response.status_code == 404:
                # Create the folder
                create_folder_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children"
                folder_data = {
                    "name": SP_FOLDER_PATH,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "rename"
                }
                create_response = requests.post(create_folder_url, headers=headers, json=folder_data)
                create_response.raise_for_status()
                logger.info(f"Created folder '{SP_FOLDER_PATH}' in SharePoint")
            else:
                folder_response.raise_for_status()
                logger.info(f"Folder '{SP_FOLDER_PATH}' already exists")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure folder exists: {e}")
            raise
    
    def upload_csv(self, data, filename, fieldnames):
        """
        Upload data as CSV to SharePoint.
        
        Args:
            data: List of dictionaries to upload as CSV
            filename: Target filename in SharePoint
            fieldnames: List of field names for CSV header
            
        Returns:
            True if successful, raises exception otherwise
        """
        logger.info(f"Uploading {len(data)} records to SharePoint as '{filename}'")
        
        # Ensure the folder exists
        self.ensure_folder_exists()
        
        # Get IDs and headers
        site_id = self.get_site_id()
        drive_id = self.get_drive_id()
        headers = self.get_headers()
        
        # Create CSV content in memory
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()
        writer.writerows(data)
        
        # Upload to SharePoint
        upload_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{SP_FOLDER_PATH}/{filename}:/content"
        upload_headers = self.get_headers()
        upload_headers["Content-Type"] = "text/csv"
        
        try:
            upload_response = requests.put(
                upload_url, 
                headers=upload_headers, 
                data=csv_buffer.getvalue().encode('utf-8'),
                timeout=REQUEST_TIMEOUT
            )
            upload_response.raise_for_status()
            logger.info(f"Successfully uploaded {filename} to SharePoint")
            return True
        except Exception as e:
            logger.error(f"Failed to upload CSV to SharePoint: {e}")
            raise
    
    def download_csv(self, filename):
        """
        Download a CSV file from SharePoint.
        
        Args:
            filename: The name of the file to download
            
        Returns:
            List of dictionaries representing the CSV rows, or empty list if file not found
        """
        site_id = self.get_site_id()
        drive_id = self.get_drive_id()
        headers = self.get_headers()
        
        try:
            # Get the file item to extract download URL
            file_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{SP_FOLDER_PATH}/{filename}"
            file_response = requests.get(file_url, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if file_response.status_code == 404:
                logger.warning(f"File '{filename}' not found in SharePoint")
                return []
            
            file_response.raise_for_status()
            
            # Get the download URL
            download_url = file_response.json()["@microsoft.graph.downloadUrl"]
            
            # Download the file content
            csv_response = requests.get(download_url, timeout=REQUEST_TIMEOUT)
            csv_response.raise_for_status()
            
            # Parse CSV content
            csv_content = csv_response.text.splitlines()
            reader = csv.DictReader(csv_content)
            
            return list(reader)
            
        except Exception as e:
            logger.error(f"Failed to download CSV from SharePoint: {e}")
            return []
    
    def append_to_csv(self, data, filename, fieldnames):
        """
        Download existing CSV, append new data, and upload back to SharePoint.
        
        Args:
            data: New data to append
            filename: Target filename in SharePoint
            fieldnames: Field names for CSV header
            
        Returns:
            True if successful
        """
        # Get existing data
        existing_data = self.download_csv(filename)
        logger.info(f"Downloaded {len(existing_data)} existing records from '{filename}'")
        
        # Add the current run timestamp to new data
        timestamp = datetime.now().isoformat()
        for item in data:
            item['timestamp'] = timestamp
        
        # Combine existing and new data
        combined_data = existing_data + data
        logger.info(f"Uploading {len(combined_data)} total records to '{filename}'")
        
        # Upload the combined data
        return self.upload_csv(combined_data, filename, fieldnames)

# Create a global instance of the SharePoint client
sharepoint_client = SharePointClient()