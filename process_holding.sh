#!/bin/bash

# Script to process attachments from the holding folder in Proton Mail

# This script uses 1Password CLI to get credentials for Proton Mail
# Make sure 1Password CLI is installed and you're signed in

# Run the Python script with command-line arguments
python process_proton_attachments.py --folder holding --drop ../Holding/Drop --config-file holding_last_check.json

# Exit with the same status as the Python script
exit $?