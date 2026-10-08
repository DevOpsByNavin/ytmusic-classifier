import os
import csv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def export_playlists_to_csv():
    token_file = 'credentials/token.json'
    csv_file = 'data/playlists.csv'
    creds = None

    # 1. Load the credentials from the token.json file
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file)
    else:
        print(f"Error: '{token_file}' not found in the current directory.")
        return

    # 2. Refresh the token if it has expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save the refreshed token back to token.json
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    # 3. Build the YouTube service client
    youtube = build('youtube', 'v3', credentials=creds)
    next_page_token = None
    playlist_count = 0

    print(f"Fetching your YouTube playlists and saving to '{csv_file}'...")

    # 4. Open the CSV file and set up the writer
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # Added 'Playlist ID' to the column headers
        writer.writerow(['Playlist ID', 'Title', 'Description'])

        # 5. Fetch playlists (handles pagination)
        while True:
            request = youtube.playlists().list(
                part="snippet",
                mine=True,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()

            # 6. Extract the ID, title, and description, then write them to the CSV
            for item in response.get('items', []):
                playlist_count += 1
                playlist_id = item['id']  # Extracted the playlist ID
                title = item['snippet']['title']
                description = item['snippet']['description']
                
                # Included playlist_id in the row write
                writer.writerow([playlist_id, title, description])

            # Check if there's another page of playlists
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

    print(f"Success! {playlist_count} playlists have been exported to {csv_file}.")

if __name__ == '__main__':
    export_playlists_to_csv()