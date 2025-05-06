"""
Script Runner Utility for Healing Hands Data Automation Dashboard

This module provides functions to run automation scripts and 
track their execution for the dashboard with enhanced logging.
"""

import importlib
import traceback
import sys
import time
from datetime import datetime
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

def run_script_with_output(script_path):
    """
    Run a Python script by its module path and capture its output
    with enhanced logging for progress visibility.
    
    Args:
        script_path: Module path to the script (e.g., "scripts.patients_csv")
        
    Returns:
        Tuple of (status, output) where status is "SUCCESS" or "ERROR"
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting execution of {script_path}...")
    
    # Capture stdout and stderr
    stdout_buffer = StringIO()
    stderr_buffer = StringIO()
    
    try:
        # Import the module
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Importing module {script_path}...")
        module = importlib.import_module(script_path)
        
        # Capture the script's output
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running main function from {script_path}...")
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            # Run the main function
            if hasattr(module, 'main'):
                result = module.main()
            else:
                raise AttributeError(f"Module {script_path} has no main() function")
        
        # Process output
        stdout_output = stdout_buffer.getvalue()
        stderr_output = stderr_buffer.getvalue()
        
        # Add timestamps to each line of output for better visibility
        timestamped_output = []
        for line in (stdout_output + stderr_output).splitlines():
            if line.strip():  # Skip empty lines
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # Only add timestamp if line doesn't already have one (from logger)
                if ' - INFO - ' in line or ' - ERROR - ' in line or ' - WARNING - ' in line:
                    timestamped_output.append(line)
                else:
                    timestamped_output.append(f"[{timestamp}] {line}")
        
        output = '\n'.join(timestamped_output)
        
        # Add final status message
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if result is True:
            output += f"\n[{timestamp}] Script execution completed successfully!"
            return "SUCCESS", output
        else:
            output += f"\n[{timestamp}] Script execution failed with an error."
            return "ERROR", output
    
    except Exception as e:
        # Capture any exceptions
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        error_output = f"[{timestamp}] Exception: {str(e)}\n"
        error_output += traceback.format_exc()
        
        # Add any output that might have been captured before the error
        error_output += f"\n[{timestamp}] Output before error:\n"
        
        # Process captured output
        stdout_output = stdout_buffer.getvalue()
        stderr_output = stderr_buffer.getvalue()
        
        # Add timestamps to each line of captured output
        timestamped_output = []
        for line in (stdout_output + stderr_output).splitlines():
            if line.strip():  # Skip empty lines
                line_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # Only add timestamp if line doesn't already have one (from logger)
                if ' - INFO - ' in line or ' - ERROR - ' in line or ' - WARNING - ' in line:
                    timestamped_output.append(line)
                else:
                    timestamped_output.append(f"[{line_timestamp}] {line}")
        
        error_output += '\n'.join(timestamped_output)
        error_output += f"\n[{timestamp}] Script execution failed with an exception."
        
        return "ERROR", error_output