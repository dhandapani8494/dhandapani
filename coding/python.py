#!/usr/bin/env python3
"""
Infrastructure automation client for REST API operations.

This script:
1. Reads and validates JSON from a file
2. Filters objects where 'private' is False
3. Posts the filtered data to a REST endpoint
4. Processes the response to print keys with 'valid': true
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

def read_and_validate_json(file_path: str) -> Dict[str, Any]:
    """
    Read and validate JSON from file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON data as dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
        ValueError: If JSON root is not an object
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not isinstance(data, dict):
            raise ValueError("JSON root must be an object (dictionary)")
            
        logger.info(f"Successfully read and validated JSON from {file_path}")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise

def filter_private_objects(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter the JSON structure to only include objects where 'private' is False.
    
    This assumes the top-level keys map to objects that may contain a 'private' field.
    Only top-level objects are filtered; nested structures within values are preserved.
    
    Args:
        data: Input JSON dictionary
        
    Returns:
        Filtered dictionary containing only non-private objects
    """
    filtered = {}
    
    for key, value in data.items():
        # Check if value is a dictionary and has 'private' field
        if isinstance(value, dict):
            private_value = value.get('private')
            # Include if 'private' is explicitly False (not just falsy)
            if private_value is False:
                filtered[key] = value
        else:
            # If value is not a dict, we can't check 'private', so exclude it
            logger.debug(f"Skipping key '{key}' - value is not an object")
    
    logger.info(f"Filtered {len(data)} objects down to {len(filtered)} non-private objects")
    return filtered

def post_to_service(data: Dict[str, Any], base_url: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Post data to the REST service endpoint.
    
    Args:
        data: JSON data to post
        base_url: Base URL of the service (e.g., 'https://api.example.com')
        timeout: Request timeout in seconds
        
    Returns:
        JSON response from server
        
    Raises:
        requests.RequestException: On HTTP/network errors
        json.JSONDecodeError: If response is not valid JSON
    """
    endpoint = f"{base_url.rstrip('/')}/service/generate"
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    try:
        logger.info(f"POSTing to {endpoint}")
        response = session.post(
            endpoint,
            json=data,
            timeout=timeout,
            headers={'Content-Type': 'application/json'}
        )
        
        # Raise an exception for bad status codes
        response.raise_for_status()
        
        # Parse JSON response
        try:
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Response JSON root must be an object")
            logger.info(f"Received successful response with {len(result)} objects")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in response: {e}")
            logger.debug(f"Response content: {response.text}")
            raise
            
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.debug(f"Response body: {e.response.text}")
        raise
    finally:
        session.close()

def process_response(response_data: Dict[str, Any]) -> List[str]:
    """
    Extract keys from response where child attribute 'valid' is True.
    
    Args:
        response_data: JSON response dictionary
        
    Returns:
        List of keys that have 'valid': True
    """
    valid_keys = []
    
    for key, value in response_data.items():
        if isinstance(value, dict):
            if value.get('valid') is True:
                valid_keys.append(key)
        else:
            logger.debug(f"Skipping key '{key}' in response - value is not an object")
    
    logger.info(f"Found {len(valid_keys)} objects with 'valid': true")
    return valid_keys

def main(input_file: str = "example.json", service_url: str = "https://localhost:8443") -> int:
    """
    Main execution function.
    
    Args:
        input_file: Path to input JSON file
        service_url: Base URL of the target service
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Step 1: Read and validate JSON
        raw_data = read_and_validate_json(input_file)
        
        # Step 2: Filter private objects
        filtered_data = filter_private_objects(raw_data)
        
        if not filtered_data:
            logger.warning("No non-private objects found in input data")
            return 0
            
        # Step 3: Post to service
        response_data = post_to_service(filtered_data, service_url)
        
        # Step 4: Process response and print valid keys
        valid_keys = process_response(response_data)
        
        # Print results to stdout (as requested)
        for key in valid_keys:
            print(key)
            
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        return 1
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return 1
    except requests.exceptions.RequestException as e:
        logger.error(f"Service communication error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Infrastructure automation client")
    parser.add_argument(
        "--input-file", 
        default="example.json",
        help="Path to input JSON file (default: example.json)"
    )
    parser.add_argument(
        "--service-url", 
        default="https://localhost:8443",
        help="Base URL of the target service (default: https://localhost:8443)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    sys.exit(main(args.input_file, args.service_url))