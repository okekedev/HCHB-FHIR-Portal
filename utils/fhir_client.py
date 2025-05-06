"""
FHIR API client for Healing Hands automation scripts.
Handles authentication, token management, and API requests.
"""
import requests
import socket
import threading
import logging
import time

# Import configuration
from utils.config import (
    CLIENT_ID, RESOURCE_SECURITY_ID, AGENCY_SECRET, TOKEN_URL,
    API_BASE_URL, REQUEST_TIMEOUT, TOKEN_ROTATION_COUNT, MAX_RETRIES
)

logger = logging.getLogger(__name__)

class TokenManager:
    """Manages token rotation for API requests"""
    
    def __init__(self):
        self.request_count = 0
        self.current_token = None
        self.lock = threading.Lock()
    
    def get_token(self, force_refresh=False):
        """
        Get the current token, refreshing if needed.
        
        Args:
            force_refresh: Force a token refresh regardless of counter
            
        Returns:
            Current valid bearer token
        """
        with self.lock:
            if force_refresh or not self.current_token or self.request_count >= TOKEN_ROTATION_COUNT:
                self.current_token = self._fetch_new_token()
                self.request_count = 0
                logger.info(f"Token refreshed. Reset request counter to 0.")
            
            return self.current_token
    
    def _fetch_new_token(self):
        """Fetch a new bearer token from the API"""
        data = {
            "grant_type": "agency_auth",
            "client_id": CLIENT_ID,
            "scope": "openid HCHB.api.scope agency.identity hchb.identity",
            "resource_security_id": RESOURCE_SECURITY_ID,
            "agency_secret": AGENCY_SECRET,
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Requesting new bearer token (attempt {attempt+1}/{MAX_RETRIES})...")
                response = requests.post(TOKEN_URL, data=data, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                token = response.json()["access_token"]
                logger.info("Successfully obtained new bearer token")
                return token
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Token request failed: {e}. Retrying...")
                    # Clear connection pool before retry
                    requests.Session().close()
                    try:
                        socket.getaddrinfo.cache_clear()
                    except:
                        pass  # Handle case where this method is not available
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to obtain token after {MAX_RETRIES} attempts: {e}")
                    raise
    
    def increment_request_count(self):
        """
        Increment the request counter and check if token rotation is needed.
        
        Returns:
            True if token needs to be refreshed, False otherwise
        """
        with self.lock:
            self.request_count += 1
            logger.debug(f"Request count: {self.request_count}/{TOKEN_ROTATION_COUNT}")
            
            if self.request_count >= TOKEN_ROTATION_COUNT:
                logger.info(f"Reached {TOKEN_ROTATION_COUNT} requests. Token rotation needed.")
                return True
            return False

# Initialize global token manager
token_manager = TokenManager()

class FHIRClient:
    """Client for making requests to the FHIR API"""
    
    def __init__(self):
        """Initialize the FHIR client"""
        self.base_url = API_BASE_URL
        
    def get_headers(self):
        """Get authentication headers with current token"""
        token = token_manager.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/fhir+json"
        }
        
    def make_request(self, endpoint, params=None, headers=None, retry_count=0):
        """
        Make an API request with token rotation.
        
        Args:
            endpoint: API endpoint to request (will be appended to base URL if not a full URL)
            params: Optional request parameters
            headers: Optional request headers (auth will be added)
            retry_count: Current retry attempt
            
        Returns:
            The response JSON
        """
        # Construct the URL if endpoint is not a full URL
        if endpoint.startswith("http"):
            url = endpoint
        else:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Get current headers and merge with custom headers if provided
        request_headers = self.get_headers()
        if headers:
            request_headers.update(headers)
        
        try:
            if params:
                response = requests.get(url, params=params, headers=request_headers, timeout=REQUEST_TIMEOUT)
            else:
                response = requests.get(url, headers=request_headers, timeout=REQUEST_TIMEOUT)
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limit hit. Waiting {retry_after}s before retrying...")
                time.sleep(retry_after)
                
                # Force token rotation
                new_token = token_manager.get_token(force_refresh=True)
                request_headers["Authorization"] = f"Bearer {new_token}"
                
                # Retry with new token
                if retry_count < MAX_RETRIES:
                    logger.info(f"Retrying request with new token (attempt {retry_count+1}/{MAX_RETRIES})...")
                    return self.make_request(endpoint, params, headers, retry_count + 1)
                else:
                    logger.error(f"Failed after {MAX_RETRIES} retry attempts")
                    response.raise_for_status()
            
            # For URI Too Long errors (414), adjust the query
            if response.status_code == 414:
                logger.warning("URI Too Long error (414). Need to use smaller batch size.")
                return None
            
            # For server errors, retry with exponential backoff
            if response.status_code >= 500:
                retry_wait = 2 ** retry_count  # Exponential backoff
                logger.warning(f"Server error {response.status_code}. Waiting {retry_wait}s before retrying...")
                time.sleep(retry_wait)
                
                # Retry with new token
                if retry_count < MAX_RETRIES:
                    # Force token rotation
                    new_token = token_manager.get_token(force_refresh=True)
                    request_headers["Authorization"] = f"Bearer {new_token}"
                    logger.info(f"Retrying request with new token (attempt {retry_count+1}/{MAX_RETRIES})...")
                    return self.make_request(endpoint, params, headers, retry_count + 1)
                else:
                    logger.error(f"Failed after {MAX_RETRIES} retry attempts")
                    response.raise_for_status()
            
            # For other errors, just raise
            response.raise_for_status()
            
            # Increment request count after successful request
            token_manager.increment_request_count()
            
            # Return the JSON response
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 414:
                logger.warning("URI Too Long error (414). Need to use smaller batch size.")
                return None
                
            if retry_count < MAX_RETRIES:
                logger.warning(f"HTTP error: {e}. Retrying with new token...")
                # Force token rotation for any HTTP error
                new_token = token_manager.get_token(force_refresh=True)
                request_headers["Authorization"] = f"Bearer {new_token}"
                return self.make_request(endpoint, params, headers, retry_count + 1)
            else:
                logger.error(f"Failed after {MAX_RETRIES} retry attempts: {e}")
                raise
        except Exception as e:
            if retry_count < MAX_RETRIES:
                logger.warning(f"Request error: {e}. Retrying...")
                # Clear connection pool and reset socket for other errors
                requests.Session().close()
                try:
                    socket.getaddrinfo.cache_clear()
                except:
                    pass  # Handle case where this method is not available
                
                time.sleep(2 ** retry_count)  # Exponential backoff
                return self.make_request(endpoint, params, headers, retry_count + 1)
            else:
                logger.error(f"Failed after {MAX_RETRIES} retry attempts: {e}")
                raise
    
    def get_resource(self, resource_type, resource_id, params=None):
        """
        Get a specific FHIR resource by its ID.
        
        Args:
            resource_type: The FHIR resource type (Patient, Practitioner, etc.)
            resource_id: The ID of the resource
            params: Optional query parameters
            
        Returns:
            Resource data as JSON
        """
        endpoint = f"{resource_type}/{resource_id}"
        return self.make_request(endpoint, params=params)
    
    def search_resources(self, resource_type, params=None):
        """
        Search for FHIR resources of a specific type.
        
        Args:
            resource_type: The FHIR resource type to search for
            params: Search parameters
            
        Returns:
            Bundle of resources matching the search criteria
        """
        return self.make_request(resource_type, params=params)
    
    def get_all_pages(self, resource_type, params=None):
        """
        Get all pages of a search result by following 'next' links.
        
        Args:
            resource_type: The FHIR resource type to search for
            params: Search parameters for the initial request
            
        Returns:
            List of all resources from all pages
        """
        all_resources = []
        page_count = 0
        
        # Get the first page
        bundle = self.search_resources(resource_type, params)
        
        # Process the first page
        if "entry" in bundle and bundle["entry"]:
            for entry in bundle["entry"]:
                if "resource" in entry:
                    all_resources.append(entry["resource"])
            
            page_count += 1
            logger.info(f"Retrieved page {page_count} with {len(bundle.get('entry', []))} resources")
        
        # Follow 'next' links for additional pages
        while "link" in bundle:
            next_link = next((link for link in bundle["link"] if link.get("relation") == "next"), None)
            if next_link and "url" in next_link:
                bundle = self.make_request(next_link["url"])
                
                if "entry" in bundle and bundle["entry"]:
                    for entry in bundle["entry"]:
                        if "resource" in entry:
                            all_resources.append(entry["resource"])
                    
                    page_count += 1
                    logger.info(f"Retrieved page {page_count} with {len(bundle.get('entry', []))} resources")
                else:
                    break
            else:
                break
        
        logger.info(f"Retrieved {len(all_resources)} total resources of type {resource_type}")
        return all_resources

# Create a global instance of the FHIR client
fhir_client = FHIRClient()