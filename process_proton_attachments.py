#!/usr/bin/env python3

import os
import json
import argparse
import subprocess
from datetime import datetime, timezone
import time
import re
import signal
import sys
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from functools import wraps

from dotenv import load_dotenv
import logging
from protonmail import ProtonMail
from protonmail.models import Message, Attachment, Label

# Load environment variables
load_dotenv()

# Constants
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Timeout decorator
def timeout(seconds=10, error_message="Function call timed out"):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        @wraps(func)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result
        return wrapper
    return decorator

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename."""
    # Remove or replace invalid filename characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace spaces and multiple dashes with single dash
    filename = re.sub(r'[\s-]+', '-', filename)
    return filename.strip('-')

def load_last_check_date(config_file="last_check.json") -> Optional[str]:
    """Load the last check date from config file."""
    try:
        with open(config_file, 'r') as f:
            data = json.load(f)
            return data.get('last_check')
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_last_check_date(date: str, config_file="last_check.json") -> None:
    """Save the last check date to config file."""
    with open(config_file, 'w') as f:
        json.dump({'last_check': date}, f)

def get_timestamp_from_iso(iso_date: Optional[str]) -> Optional[int]:
    """Convert ISO date string to timestamp."""
    if not iso_date:
        return None
    try:
        dt = datetime.strptime(iso_date, DATE_FORMAT)
        dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None

# Function to handle 2FA if needed
def get_2fa_code():
    print("\n" + "="*50)
    print("TWO-FACTOR AUTHENTICATION REQUIRED")
    print("="*50)
    code = input("Enter 2FA code: ")
    print("="*50 + "\n")
    return code

@timeout(300, "ProtonMail processing timed out after 5 minutes")
def get_proton_credentials() -> Dict[str, Any]:
    """Get Proton Mail credentials from 1Password CLI."""
    try:
        op_executable = shutil.which("op")
        if not op_executable:
            raise FileNotFoundError("1Password CLI 'op' not found. Please ensure it is installed and in your PATH.")

        # Get the Proton item from 1Password
        result = subprocess.run(
            [op_executable, "item", "get", "Proton", "--vault", "Private", "--format", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the JSON output
        item_data = json.loads(result.stdout)
        
        # Extract the credentials
        credentials = {
            "username": None,
            "password": None,
            "totp": None
        }
        
        # Extract fields
        for field in item_data.get("fields", []):
            if field.get("id") == "username":
                credentials["username"] = field.get("value")
            elif field.get("id") == "password":
                credentials["password"] = field.get("value")
            elif field.get("id") == "one-time password" or field.get("type") == "OTP":
                credentials["totp"] = field.get("totp")
        
        if not all([credentials["username"], credentials["password"]]):
            raise ValueError("Could not find username or password in 1Password")
        
        return credentials
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running 1Password CLI: {e}")
        logger.error(f"Stdout: {e.stdout}")
        logger.error(f"Stderr: {e.stderr}")
        raise
    except json.JSONDecodeError:
        logger.error("Error parsing 1Password CLI output")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

def process_emails(proton_folder=None, drop_folder=None, config_file="last_check.json"):
    """Main function to process emails and save attachments."""
    # Get credentials from 1Password
    logger.info("Getting credentials from 1Password...")
    credentials = get_proton_credentials()
    username = credentials["username"]
    password = credentials["password"]
    totp_code = credentials["totp"]
    
    # Use command-line arguments if provided, otherwise fall back to environment variables
    label_path = proton_folder or os.getenv('PROTON_FOLDER')
    logger.info(f"Looking for label with path: '{label_path}'")
    
    drop_folder_path = drop_folder or os.getenv('DROP_FOLDER', 'attachments')
    drop_folder = Path(drop_folder_path)
    logger.info(f"Using drop folder: '{drop_folder}'")

    if not all([username, password, label_path]):
        raise ValueError("Missing required credentials or folder information")

    # Create drop folder if it doesn't exist
    drop_folder.mkdir(parents=True, exist_ok=True)

    # Initialize ProtonMail client
    logger.info("Initializing ProtonMail client...")
    client = ProtonMail(logging_level=2)  # 2 = INFO level
    
    try:
        # Login to ProtonMail
        logger.info(f"Logging in as {username}...")
        # If we have a TOTP code from 1Password, create a function that returns it
        if totp_code:
            logger.info("Using 2FA code from 1Password")
            def get_2fa_from_1password():
                logger.info(f"Using 2FA code: {totp_code}")
                return totp_code
            client.login(username, password, getter_2fa_code=get_2fa_from_1password)
        else:
            # Fall back to manual 2FA input
            logger.info("No 2FA code from 1Password, will prompt for manual input")
            client.login(username, password, getter_2fa_code=get_2fa_code)
        logger.info("Login successful")
        
        # Get last check date
        last_check_iso = load_last_check_date(config_file)
        last_check_timestamp = get_timestamp_from_iso(last_check_iso)
        current_time = datetime.now(timezone.utc).strftime(DATE_FORMAT)
        
        logger.info(f"Last check date: {last_check_iso or 'Never'}")
        
        # Get user labels
        logger.info("Getting labels...")
        user_labels = client.get_all_labels()
        
        # Log all available labels for debugging
        logger.info("Available labels:")
        for label in user_labels:
            logger.info(f"  - {label.name} (ID: {label.id}, Path: {getattr(label, 'path', 'N/A')})")
        
        # Find the label that matches the path
        target_label = None
        
        # First try exact match
        for label in user_labels:
            if label.name == label_path:
                target_label = label
                break
        
        # If not found, try case-insensitive match
        if not target_label:
            for label in user_labels:
                if label.name.lower() == label_path.lower():
                    target_label = label
                    break
        
        # If still not found, try to match with path parts
        if not target_label:
            path_parts = label_path.split('/')
            
            # Try to find a label that contains all parts of the path
            for label in user_labels:
                label_name_lower = label.name.lower()
                all_parts_match = True
                
                for part in path_parts:
                    if part.lower() not in label_name_lower:
                        all_parts_match = False
                        break
                
                if all_parts_match:
                    target_label = label
                    break
        
        if not target_label:
            raise ValueError(f"Label '{label_path}' not found")
        
        logger.info(f"Found label: {target_label.name} (ID: {target_label.id})")
        
        # Get messages with the specified label
        logger.info(f"Getting messages with label '{target_label.name}'...")
        messages = client.get_messages(label_or_id=target_label.id)
        
        # Filter messages by date if we have a last check date
        if last_check_timestamp:
            messages = [msg for msg in messages if msg.time > last_check_timestamp]
        
        logger.info(f"Found {len(messages)} new messages")
        
        # Process messages
        for msg in messages:
            # Read the message to get its content and attachments
            full_msg = client.read_message(msg)
            
            # Get sender information
            sender_name = full_msg.sender.name or full_msg.sender.address
            sender = sanitize_filename(sender_name)
            
            # Format date
            msg_time = datetime.fromtimestamp(full_msg.time, timezone.utc)
            date_str = msg_time.strftime('%Y%m%d')
            
            # Check if message has attachments
            if full_msg.attachments:
                logger.info(f"Message '{full_msg.subject}' has {len(full_msg.attachments)} attachments")
                
                # Download attachments
                attachments = client.download_files(full_msg.attachments)
                
                for attachment in attachments:
                    # Check if it's a PDF or ZIP file
                    if attachment.name.lower().endswith(('.pdf', '.zip')):
                        file_type = "PDF" if attachment.name.lower().endswith('.pdf') else "ZIP"
                        logger.info(f"Processing {file_type} attachment: {attachment.name}")
                        
                        # Create filename
                        filename = f"{date_str}-{sender}-{sanitize_filename(attachment.name)}"
                        file_path = drop_folder / filename
                        
                        # Save attachment
                        with open(file_path, 'wb') as f:
                            f.write(attachment.content)
                            
                        logger.info(f"Saved attachment: {filename}")
        
        # Save current time as last check date
        save_last_check_date(current_time, config_file)
        logger.info(f"Updated last check date to: {current_time}")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        # No explicit logout method in the client
        logger.info("Process completed")
if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Process attachments from ProtonMail.')
    parser.add_argument('--folder', dest='proton_folder', help='ProtonMail folder/label to process')
    parser.add_argument('--drop', dest='drop_folder', help='Folder to save attachments to')
    parser.add_argument('--config-file', dest='config_file', help='Path to config file for last check date')
    
    args = parser.parse_args()
    
    # Process emails with the provided arguments
    config_file = args.config_file or "last_check.json"
    if args.config_file:
        logger.info(f"Using config file: {config_file}")
    
    process_emails(
        proton_folder=args.proton_folder,
        drop_folder=args.drop_folder,
        config_file=config_file
    )
