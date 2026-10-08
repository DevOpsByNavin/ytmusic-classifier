import os
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- CONFIGURABLE VARIABLES ---
TOKEN_PATH = os.path.join("credentials", "token.json")

def get_youtube_service():
    if not os.path.exists(TOKEN_PATH):
        print(f"[-] Missing {TOKEN_PATH}. Ensure it exists in the credentials folder.")
        sys.exit(1)
        
    # FIX: We removed the hardcoded `scopes=[...]` parameter!
    # Now it will safely use the exact scopes stored inside your token.json
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    
    return build('youtube', 'v3', credentials=creds)

def fetch_liked_videos(service, max_results=100):
    """Fetches recently liked videos. Paginate through results.

    If max_results is None, fetch all available liked videos (no artificial cap).
    """
    videos = []
    try:
        # YouTube API allows up to 50 results per page
        request = service.videos().list(part="snippet", myRating="like", maxResults=50)

        while request:
            response = request.execute()
            for item in response.get("items", []):
                videos.append({
                    "id": item["id"],
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "url": f"https://www.youtube.com/watch?v={item['id']}"
                })

                # If a numeric max_results was provided, stop when reached
                if max_results is not None and len(videos) >= max_results:
                    return videos

            # Move to next page; when there is no next page, request becomes None and loop ends
            request = service.videos().list_next(request, response)

        return videos
    except HttpError as e:
        if e.resp.status in [403] and "quotaExceeded" in str(e):
            print("\n[!] YOUTUBE QUOTA EXCEEDED while fetching videos. Stopping execution for today.")
            sys.exit(1)
        raise e

def add_video_to_playlist(service, video_id, playlist_id):
    """Inserts a video into a target playlist."""
    try:
        service.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id}
                }
            }
        ).execute()
        return True
    except HttpError as e:
        if e.resp.status in [403] and "quotaExceeded" in str(e):
            print("\n[!] YOUTUBE QUOTA EXCEEDED while syncing to playlist. Stopping execution for today.")
            sys.exit(1)
        elif e.resp.status == 404:
            print(f"[-] Video {video_id} or Playlist {playlist_id} not found. Skipping.")
            return False
        else:
            print(f"[-] Error syncing video {video_id}: {e}")
            return False