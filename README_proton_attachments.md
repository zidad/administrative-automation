# ProtonMail Attachment Processor

This tool automatically downloads attachments from specified folders in your ProtonMail account.

## Setup

1. Make sure you have Python 3.6+ installed
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Install 1Password CLI:
   - On macOS: `brew install --cask 1password-cli`
   - On other platforms: [1Password CLI Installation Guide](https://developer.1password.com/docs/cli/get-started/)
4. Make sure you're signed in to 1Password CLI:
   ```
   op signin
   ```
5. Create a "Proton" item in your 1Password vault with:
   - Username: Your ProtonMail email
   - Password: Your ProtonMail password
   - One-time password: Set up TOTP for your ProtonMail account

## Usage

### Command-line Arguments

The script supports the following command-line arguments:

- `--folder`: The ProtonMail folder/label to process
- `--drop`: The folder where attachments will be saved
- `--config-file`: Path to the config file for tracking the last check date

Example:
```
python process_proton_attachments.py --folder werkmaatschappij --drop ../drop --config-file werkmaatschappij_last_check.json
```

### Shell Scripts

For convenience, two shell scripts are provided:

1. `process_werkmaatschappij.sh`: Processes attachments from the "werkmaatschappij" folder
   ```
   ./process_werkmaatschappij.sh
   ```

2. `process_holding.sh`: Processes attachments from the "holding" folder
   ```
   ./process_holding.sh
   ```

### Creating Additional Configurations

To create a configuration for a different folder:

1. Create a new shell script (e.g., `process_newfolder.sh`):
   ```bash
   #!/bin/bash
   
   # Script to process attachments from the newfolder in Proton Mail
   
   # Run the Python script with command-line arguments
   python process_proton_attachments.py --folder newfolder --drop ../NewFolder/Drop --config-file newfolder_last_check.json
   
   # Exit with the same status as the Python script
   exit $?
   ```

2. Make it executable:
   ```
   chmod +x process_newfolder.sh
   ```

## Features

- Downloads PDF and ZIP attachments from specified ProtonMail folders
- Tracks the last check date to only process new messages
- Saves attachments with a standardized naming convention: `YYYYMMDD-Sender-Filename`
- Creates separate configurations for different folders with their own tracking files

## Troubleshooting

- If you encounter authentication issues, make sure your ProtonMail credentials in 1Password are correct
- If the 1Password CLI integration isn't working, you can fall back to manual 2FA input
- Make sure the 1Password CLI is installed and you're signed in
- Check the log output for detailed information about the process
- If you get an error about the 1Password CLI not being found, make sure the path in the script matches your installation path