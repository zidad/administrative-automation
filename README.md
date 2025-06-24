# ProtonMail Attachment Processor

This script automatically processes emails from your ProtonMail account, downloading PDF attachments from messages with a specific tag.

## Setup

1. Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Edit the `.env` file with your:
   - ProtonMail username
   - ProtonMail password
   - Tag to filter emails
   - Drop folder path for attachments

## Usage

Run the script:
```bash
python process_proton_attachments.py
```

The script will:
1. Check for new emails with the specified tag
2. Download PDF attachments
3. Save them in the drop folder with format: `{YYYYMMDD}-{sanitized-sender-name}-{filename}`
4. Track the last check date to avoid reprocessing emails

## Security Note

Store your `.env` file securely and never commit it to version control.
