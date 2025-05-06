"""
Centralized logging configuration for Healing Hands automation scripts.
"""
import logging
import os
from datetime import datetime
from utils.config import OUTPUT_DIRECTORY

def configure_logging(script_name, level=logging.INFO, log_to_file=True):
    """
    Configure logging for a script.
    
    Args:
        script_name: Name of the script for log filename
        level: Logging level (default: INFO)
        log_to_file: Whether to log to a file in addition to console
        
    Returns:
        Logger instance
    """
    # Create logger
    logger = logging.getLogger(script_name)
    logger.setLevel(level)
    
    # Remove existing handlers (in case logging is reconfigured)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add console handler to logger
    logger.addHandler(console_handler)
    
    # Optionally add file handler
    if log_to_file:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(OUTPUT_DIRECTORY, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = os.path.join(logs_dir, f'{script_name}_{timestamp}.log')
        
        # Create file handler
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        
        # Add file handler to logger
        logger.addHandler(file_handler)
    
    logger.info(f"Logging configured for {script_name}")
    return logger

def get_script_logger(script_name):
    """
    Get a logger for a script. If the logger doesn't exist, it will be created.
    
    Args:
        script_name: Name of the script
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(script_name)
    
    # If logger doesn't have handlers, configure it
    if not logger.handlers:
        return configure_logging(script_name)
    
    return logger