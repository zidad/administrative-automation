# ProtonMail Attachment Processor

This script automatically processes emails from your ProtonMail account, downloading PDF attachments from messages with a specific tag.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up 1Password:**
    - Ensure the 1Password CLI (`op`) is installed and you are signed in.
    - Create an item in your "Private" vault named `Proton`.
    - Add your ProtonMail `username` and `password` to the fields.
    - If you use two-factor authentication, add a `one-time password` field. The script will automatically use this for 2FA.

3.  **Configure Folders:**
    You can configure the ProtonMail label/folder and the download drop folder in one of two ways:

    *   **Command-line arguments (recommended):**
        Pass the folders directly when running the script. See the [Usage](#usage) section.

    *   **Environment variables:**
        Create a `.env` file in the project root and add the following:
        ```
        PROTON_FOLDER="Your/Proton/Label"
        DROP_FOLDER="path/to/your/drop_folder"
        ```

## Usage

Run the script with the required folder arguments:
```bash
python process_proton_attachments.py --folder "Your/Proton/Label" --drop "path/to/your/drop_folder"
```

If you have set environment variables in a `.env` file, you can run it without arguments:
```bash
python process_proton_attachments.py
```

The script will:
1.  Fetch ProtonMail credentials and 2FA code from the `Proton` item in your 1Password "Private" vault.
2.  Check for new emails in the specified folder/label.
3.  Download PDF and ZIP attachments.
4.  Save them in the drop folder with the format: `{YYYYMMDD}-{sanitized-sender-name}-{filename}`.
5.  Track the last check date to avoid reprocessing emails.
