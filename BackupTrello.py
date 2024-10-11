from sys import exit
import requests
import csv
import os
import json
from cryptography.fernet import Fernet
from tkinter import Tk, Toplevel, Checkbutton, Button, IntVar, simpledialog, messagebox, Text, Scrollbar, END
from tkinter.filedialog import askdirectory
from datetime import datetime

CONFIG_FILE = "config.json"
CREDENTIALS_FILE = "credentials.enc"
ENCRYPTION_KEY_FILE = "encryption.key"

# MIT License - Just copy paste from someone else
MIT_LICENSE = """
MIT License

Copyright (c) 2024 - Joshua Steekamp

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

...

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# Display the license agreement
def display_license():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            if config.get("license_accepted"):
                return True  # License already accepted

    root = Tk()
    root.withdraw()  # Hide the main window

    # Display license in a message box
    accepted = messagebox.askyesno("License Agreement", MIT_LICENSE + "\n\nDo you accept the terms of the license?")
    
    #if accepted:
     #   # Save the acceptance in config file
     #   with open(CONFIG_FILE, 'w') as f:
     #       json.dump({"license_accepted": True}, f)

    root.destroy()  # Close the hidden root window
    return accepted

# Function to generate a new encryption key and save it in a file
def generate_key():
    key = Fernet.generate_key()
    with open(ENCRYPTION_KEY_FILE, 'wb') as key_file:
        key_file.write(key)
    return key

# Function to load the encryption key from the file, or generate a new one if it doesn't exist
def load_key():
    if os.path.exists(ENCRYPTION_KEY_FILE):
        with open(ENCRYPTION_KEY_FILE, 'rb') as key_file:
            return key_file.read()
    else:
        return generate_key()

# Function to encrypt and save the API key and token
def save_credentials(api_key, api_token):
    key = load_key()
    fernet = Fernet(key)
    
    credentials = json.dumps({"api_key": api_key, "api_token": api_token}).encode()
    encrypted_credentials = fernet.encrypt(credentials)
    
    with open(CREDENTIALS_FILE, 'wb') as credentials_file:
        credentials_file.write(encrypted_credentials)

# Function to load and decrypt the API key and token
def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        key = load_key()
        fernet = Fernet(key)
        
        with open(CREDENTIALS_FILE, 'rb') as credentials_file:
            encrypted_credentials = credentials_file.read()
        
        decrypted_credentials = fernet.decrypt(encrypted_credentials)
        return json.loads(decrypted_credentials)
    return None

def delete_credentials_files():
    """Delete the credentials and encryption key files."""
    if os.path.exists("credentials.enc"):
        os.remove("credentials.enc")
    if os.path.exists("encryption.key"):
        os.remove("encryption.key")

# Function to prompt for API key and token if not available
def get_api_credentials():
    credentials = load_credentials()
    if credentials:
        return credentials['api_key'], credentials['api_token']
    else:
        # If no credentials found, provide help to find them
        root = Tk()
        root.withdraw()  # Hide the main window

        instructions = (
            "To obtain your Trello API Key and Token:\n\n"
            "1. Go to the Trello Developer API Keys page: https://trello.com/app-key\n"
            "2. Your API Key will be displayed at the top of the page.\n"
            "3. To generate a Token, scroll down to the 'Token' section and click on the link.\n"
            "4. Authorize the application and copy the Token.\n\n"
            "Please enter your API Key and Token below."
        )
        
        messagebox.showinfo("Getting Trello API Key and Token", instructions)

        while True:
                api_key = simpledialog.askstring("API Key", "Please enter your Trello API Key:")
                if api_key is None:  # Check if Cancel was clicked
                    print("API Key input canceled. Exiting the application.")
                    exit(0)  # Exit the application
                if api_key:
                    break
                else:
                    messagebox.showerror("Input Error", "API Key cannot be empty. Please enter a valid API Key.")

            # Loop until valid API token is entered
        while True:
            api_token = simpledialog.askstring("API Token", "Please enter your Trello API Token:")
            if api_token is None:  # Check if Cancel was clicked
                print("API Token input canceled. Exiting the application.")
                exit(0)  # Exit the application
            if api_token:
                break
            else:
                messagebox.showerror("Input Error", "API Token cannot be empty. Please enter a valid API Token.")

        # Save the credentials for future use
        save_credentials(api_key, api_token)
        return api_key, api_token

# Function to get all workspaces (organizations) for the user
def get_all_workspaces(api_key, api_token):
    url = f"https://api.trello.com/1/members/me/organizations?key={api_key}&token={api_token}"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        print("Response text:", response.text)
        delete_credentials_files()  # Delete files if invalid credentials
        messagebox.showerror("Credential Error", "There was an issue using your credentials. Please re-run the application.")
        exit()
        return []  # Return an empty list on error
        

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        print("Error: Failed to decode JSON response.")
        print("Response text:", response.text)
        delete_credentials_files()  # Delete files if invalid credentials
        messagebox.showerror("Credential Error", "There was an issue using your credentials. Please re-run the application.")
        exit()
        return []  # Return an empty list on JSON decode error


# Function to get all boards for a workspace
def get_boards_for_workspace(api_key, api_token, workspace_id):
    url = f"https://api.trello.com/1/organizations/{workspace_id}/boards?key={api_key}&token={api_token}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Error fetching boards for workspace: {workspace_id}. Status code: {response.status_code}")
        return []  # or consider raising an exception
    return response.json()


# Function to get all cards from a specific board
def get_cards_for_board(api_key, api_token, board_id):
    url = f"https://api.trello.com/1/boards/{board_id}/cards?key={api_key}&token={api_token}"
    response = requests.get(url)
    return response.json()

# Function to load or select the backup folder
def get_backup_folder():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            folder_path = config.get("backup_folder")

            if folder_path and os.path.exists(folder_path):
                return folder_path

    while True:
        root = Tk()
        root.withdraw()
        folder_path = askdirectory(title="Select Backup Folder")

        if folder_path:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({"backup_folder": folder_path}, f)
            return folder_path
        else:
            print("No folder selected, please select a valid folder.")

# Function to create a versioned folder with timestamp and version number
def create_versioned_folder(backup_folder):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    
    version = 1
    while True:
        versioned_folder = os.path.join(backup_folder, f"{date_str}_Version{version}")
        if not os.path.exists(versioned_folder):
            os.makedirs(versioned_folder)
            break
        version += 1
    
    return versioned_folder

# Function to create and show the logging window
def create_logging_window():
    log_window = Toplevel()
    log_window.title("Backup Progress")
    
    # Set up text area for logging
    text_area = Text(log_window, wrap="word")
    text_area.pack(expand=True, fill='both')

    # Add a scrollbar to the text area
    scrollbar = Scrollbar(log_window, command=text_area.yview)
    scrollbar.pack(side='right', fill='y')
    text_area.config(yscrollcommand=scrollbar.set)

    return text_area

# Function to log messages to the logging window
def log_message(text_area, message):
    text_area.insert(END, message + "\n")
    text_area.see(END)  # Scroll to the end

# Function to select workspaces to backup
def select_workspaces(workspaces):
    selected_workspaces = []

    def on_submit():
        for i, var in enumerate(check_vars):
            if var.get():
                selected_workspaces.append(workspaces[i])
        top.quit()  # End the main loop for the top window

    root = Tk()
    root.withdraw()  # Hide the root window
    top = Toplevel(root)  # Create the selection window
    top.title("Select Workspaces to Backup")
    
    check_vars = []
    for i, workspace in enumerate(workspaces):
        var = IntVar(value=1)  # All checkboxes are enabled by default
        chk = Checkbutton(top, text=workspace['displayName'], variable=var)
        chk.pack(anchor="w")
        check_vars.append(var)

    submit_btn = Button(top, text="Submit", command=on_submit)
    submit_btn.pack()

    top.protocol("WM_DELETE_WINDOW", on_submit)  # Handle the window close event
    top.mainloop()  # Start the event loop for the selection window

    # Check if any workspaces were selected
    if not selected_workspaces:
        print("No workspaces selected. Exiting the program.")
        root.destroy()
        exit()  # Exit if no workspaces were selected

    root.destroy()  # Clean up the hidden root window
    return selected_workspaces

# Create a CSV file and write the backup data
def backup_boards_to_csv():
    # Retrieve the API key and token
    api_key, api_token = get_api_credentials()

    # Fetch workspaces
    all_workspaces = get_all_workspaces(api_key, api_token)
    
    # Select workspaces for backup
    selected_workspaces = select_workspaces(all_workspaces)
    backup_folder = get_backup_folder()

    if not backup_folder:
        print("No folder selected. Backup canceled.")
        return

    # Create versioned folder with date-time stamp and version number
    versioned_folder = create_versioned_folder(backup_folder)

    # Create and show the logging window
    log_window = create_logging_window()
    text_area = log_window
    log_message(text_area, "Starting backups...")

    # Iterate through selected workspaces
    for workspace in selected_workspaces:
        workspace_name = workspace['displayName']
        boards = get_boards_for_workspace(api_key, api_token, workspace['id'])

        for board in boards:
            board_name = board['name']
            log_message(text_area, f"Backing up board: {board_name} in workspace: {workspace_name}...")
            cards = get_cards_for_board(api_key, api_token, board['id'])
            
            # Create a CSV file for the board
            csv_file_path = os.path.join(versioned_folder, f"{workspace_name}_{board_name}.csv")
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['Card Name', 'Card ID', 'Due Date'])  # Header row

                for card in cards:
                    card_name = card['name']
                    card_id = card['id']
                    card_due = card.get('due', 'No Due Date')
                    csv_writer.writerow([card_name, card_id, card_due])

            log_message(text_area, f"Backup completed for board: {board_name} at {csv_file_path}")

    log_message(text_area, "All backups completed.")
    text_area.configure(state='disabled')  # Make the text area read-only

# Main execution
if __name__ == "__main__":
    if not display_license():
        print("You must accept the license to use this software.")
    else:
        backup_boards_to_csv()