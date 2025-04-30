#!/usr/bin/env python3
import re
import requests
import json
from backend.core.logger import get_logger

logger = get_logger(__name__)

def send_http_notification(endpoint, file_path, timeout=10):
    """Send HTTP notification to the configured endpoint.
    
    Args:
        endpoint: The URL to send the notification to
        file_path: The file path to include in the notification
        timeout: Request timeout in seconds
        
    Returns:
        bool: True if notification was successful, False otherwise
    """
    if not endpoint:
        logger.debug("No notification endpoint configured")
        return False
    
    try:
        payload = {"file_path": file_path}
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        
        logger.debug(f"Sending notification to {endpoint}: {payload}")
        response = requests.post(
            endpoint, 
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            timeout=timeout
        )
        
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Successfully sent notification for {file_path}")
            logger.debug(f"Response: {response.status_code} {response.text}")
            return True
        else:
            logger.error(f"Failed to send notification: HTTP {response.status_code}")
            logger.debug(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        return False

def extract_path_from_dat(dat_string, path_mappings=None):
    """Extracts the path portion from a 'dat=' URL string.
    
    Args:
        dat_string: The string containing a dat= parameter
        path_mappings: A list of dictionaries with 'source' and 'target' keys for path mapping
    
    Returns:
        str: The extracted path, or None if extraction failed
    """
    # First, clean the dat_string by removing any typ= or flg= parameters and anything after them
    clean_dat = dat_string
    for param in [' typ=', ' flg=', ' act=', ' cat=', ' pkg=']:
        param_pos = clean_dat.find(param)
        if param_pos != -1:
            clean_dat = clean_dat[:param_pos]
    
    # Check if the path matches any of the configured path mappings
    if path_mappings:
        for mapping in path_mappings:
            source = mapping['source']
            if source in clean_dat:
                # Extract the part after the source base path
                remaining_path = clean_dat[clean_dat.find(source) + len(source):]
                
                # Clean up the remaining path
                remaining_path = remaining_path.strip('/ ')
                
                # Combine with the target path
                target = mapping['target']
                full_path = f"{target}{remaining_path}"
                
                logger.debug(f"Using path mapping: {source} -> {target}")
                logger.debug(f"Full path: {full_path}")
                
                return full_path
    
    # If no mapping matches, use the default # separator method
    if not 'content://' in clean_dat:
        return None
        
    # Find the # character which separates the authority from the path
    hash_pos = clean_dat.find('#')
    if hash_pos != -1:
        # Get everything after the # character
        path_part = clean_dat[hash_pos + 1:]
        return path_part.strip('/ ')
    
    # Check for common Android storage paths
    # 1. External storage
    external_pos = clean_dat.find('externalstorage/')
    if external_pos != -1:
        path_part = clean_dat[external_pos + len('externalstorage/'):]
        logger.debug(f"Extracted path using externalstorage/ marker: {path_part}")
        return path_part.strip('/ ')
    
    # 2. Emulated storage
    emulated_pos = clean_dat.find('storage/emulated/0/')
    if emulated_pos != -1:
        path_part = clean_dat[emulated_pos + len('storage/emulated/0/'):]
        logger.debug(f"Extracted path using storage/emulated/0/ marker: {path_part}")
        return path_part.strip('/ ')
    
    # 3. Last resort: try to extract after the last slash
    last_slash_pos = clean_dat.rfind('/')
    if last_slash_pos != -1:
        path_part = clean_dat[last_slash_pos + 1:]
        logger.debug(f"Extracted path using last slash fallback: {path_part}")
        return path_part.strip('/ ')
    
    # If all extraction methods fail
    return None

def parse_video_path(line, path_mappings=None):
    """Extract video file path from start line using a more robust approach.
    
    Args:
        line: The log line to parse
        path_mappings: A list of dictionaries with 'source' and 'target' keys for path mapping
    
    Returns:
        str: The extracted path, or None if extraction failed
    """
    # First, find the 'dat=' parameter in the log line
    dat_pos = line.find('dat=')
    if dat_pos == -1:
        return None
        
    # Extract the content URI part starting with 'dat='
    dat_part = line[dat_pos:]
    
    # Find where the dat parameter ends
    space_after_dat = dat_part.find(' cmp=')
    if space_after_dat != -1:
        dat_part = dat_part[:space_after_dat]
    
    # Extract the actual path from the dat parameter
    path = extract_path_from_dat(dat_part, path_mappings)
    
    # Print debug info for troubleshooting
    if path:
        logger.debug(f"EXTRACTED PATH: {path}")
        logger.debug(f"FROM DAT PART: {dat_part}")
    
    return path 