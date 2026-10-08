import os
import time
import argparse
from dotenv import load_dotenv

# Import modules from src
import database as db
import youtube as yt
import ai_matcher as ai

# --- CONFIGURABLE VARIABLES ---
FETCH_LIMIT = -1         # SET TO -1 FOR UNLIMITED
AI_BATCH_LIMIT = -1       # SET TO -1 FOR UNLIMITED
SYNC_BATCH_LIMIT = -1     # SET TO -1 FOR UNLIMITED
AI_THROTTLE_DELAY = 5     # Seconds to wait between AI requests

def run_fetch_stage(yt_service):
    """Fetches liked videos and stores them in the database.

    Uses FETCH_LIMIT == -1 to indicate "unlimited" (fetch all liked videos).
    """
    # Interpret -1 as unlimited (None) so we don't pass -1 into the YT client
    limit = None if FETCH_LIMIT == -1 else FETCH_LIMIT

    if limit is None:
        print("[*] Fetching ALL liked videos (this may take a while and use API quota)...")
        liked_videos = yt.fetch_liked_videos(yt_service)
    else:
        print(f"[*] Fetching up to {limit} recent liked videos...")
        liked_videos = yt.fetch_liked_videos(yt_service, max_results=limit)

    new_count = 0
    for vid in liked_videos:
        if db.insert_liked_video(vid["id"], vid["title"], vid["channel"], vid["url"]):
            new_count += 1
    print(f"[+] Loaded {new_count} new videos into the database.")

def run_ai_stage(playlists):
    """Queries the AI to categorize uncategorized videos."""
    limit = None if AI_BATCH_LIMIT == -1 else AI_BATCH_LIMIT
    uncategorized = db.get_uncategorized_videos(limit=limit)
    print(f"\n[*] Found {len(uncategorized)} videos needing AI categorization. Processing...")
    
    for vid_id, title, channel in uncategorized:
        print(f"  -> Asking AI: '{title}' by {channel}...", end=" ")
        playlist_id = ai.categorize_song(title, channel, playlists)
        
        if playlist_id:
            db.update_video_category(vid_id, playlist_id)
            print(f"Matched! (Playlist: {playlist_id})")
        else:
            print("Failed to categorize.")
            
        time.sleep(AI_THROTTLE_DELAY)

def run_sync_stage(yt_service):
    """Syncs categorized videos to their respective YouTube playlists."""
    limit = None if SYNC_BATCH_LIMIT == -1 else SYNC_BATCH_LIMIT
    unsynced = db.get_unsynced_videos(limit=limit)
    print(f"\n[*] Found {len(unsynced)} categorized videos needing YouTube Sync. Processing...")
    
    for vid_id, playlist_id in unsynced:
        print(f"  -> Syncing video {vid_id} to playlist {playlist_id}...")
        success = yt.add_video_to_playlist(yt_service, vid_id, playlist_id)
        if success:
            db.mark_video_synced(vid_id)

def main():
    # 0. Argument Parsing
    parser = argparse.ArgumentParser(description="Automate YouTube Music playlist management.")
    parser.add_argument("--fetch", action="store_true", help="Only fetch liked videos from YouTube.")
    parser.add_argument("--categorize", action="store_true", help="Only categorize videos using the AI.")
    parser.add_argument("--sync", action="store_true", help="Only sync categorized videos to YouTube playlists.")
    args = parser.parse_args()

    # Determine which stages to run
    run_all = not any([args.fetch, args.categorize, args.sync])
    
    # 1. Setup
    print("[*] Initializing system...")
    load_dotenv()
    ai.setup_ai()
    db.load_playlists_from_csv()
    playlists = db.get_all_playlists()
    yt_service = yt.get_youtube_service()
    
    # 2. Fetch Liked Videos (Stage 1)
    if run_all or args.fetch:
        run_fetch_stage(yt_service)

    # 3. AI Categorization (Stage 2)
    if run_all or args.categorize:
        run_ai_stage(playlists)

    # 4. YouTube Playlist Sync (Stage 3)
    if run_all or args.sync:
        run_sync_stage(yt_service)
            
    print("\n[+] All tasks complete!")

if __name__ == "__main__":
    main()