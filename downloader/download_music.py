"""
A standalone music downloader that uses yt-dlp to download songs from public
YouTube playlists defined in a CSV file.

Features:
- Downloads audio in high-quality M4A format.
- Embeds metadata (artist, title, album art) and the YouTube video ID in the comments.
- Cleans filenames and titles by removing common junk keywords.
- Uses a local SQLite database to track downloaded songs and avoid re-downloads.
- Provides a clean, informative progress bar for each download.
- Organizes downloaded songs into folders based on playlist names.
"""
import os
import sys
import sqlite3
import pandas as pd
import yt_dlp
import re
from pathlib import Path

# --- Configuration ---
# The root folder where all music will be saved.
MUSIC_ROOT = Path.home() / "music"
# Path to the project's CSV file containing playlist info.
CSV_PATH = "data/playlists.csv"
# Path to the shared SQLite database.
DB_PATH = "data/music.db"


def setup_database():
    """
    Ensures the 'downloaded' table exists in the database.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS downloaded (
                video_id TEXT PRIMARY KEY,
                is_downloaded INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
        print("[*] Database setup complete.")
    except sqlite3.Error as e:
        print(f"[-] Database Error: {e}", file=sys.stderr)
        sys.exit(1)


def get_downloaded_ids():
    """
    Retrieves a set of all video IDs that have already been downloaded.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT video_id FROM downloaded WHERE is_downloaded = 1")
        ids = {row[0] for row in cursor.fetchall()}
        conn.close()
        return ids
    except sqlite3.Error as e:
        print(f"[-] Database Error: {e}", file=sys.stderr)
        return set()


def mark_as_downloaded(video_id):
    """
    Marks a video as downloaded in the database.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Use INSERT OR REPLACE to handle cases where the ID might already exist but is not marked.
        cursor.execute("INSERT OR REPLACE INTO downloaded (video_id, is_downloaded) VALUES (?, 1)", (video_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"[-] Database Error while marking '{video_id}': {e}", file=sys.stderr)


def get_playlists_from_csv():
    """
    Reads the playlists.csv file and returns a list of playlist data.
    """
    try:
        # Use header=0 to treat the first row as the header
        df = pd.read_csv(CSV_PATH, header=0, names=['id', 'title', 'description'])
        return df.to_dict('records')
    except FileNotFoundError:
        print(f"[-] Error: `{CSV_PATH}` not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[-] Error reading CSV file: {e}", file=sys.stderr)
        sys.exit(1)


def clean_title(title):
    """
    Removes common junk keywords from a song title using regex.
    """
    junk_patterns = [
        r'\[.*?\]',              # Text in square brackets [HD], [Official]
        r'\(.*?\)',              # Text in parentheses (Official Video), (Lyrics)
        r'official music video',
        r'official video',
        r'music video',
        r'lyrics',
        r'lyric video',
        r'hd',
        r'4k',
    ]
    # Combine patterns into a single regex, case-insensitive
    combined_pattern = re.compile('|'.join(junk_patterns), re.IGNORECASE)
    # Replace all found patterns with an empty string
    cleaned_title = combined_pattern.sub('', title)
    # Remove extra whitespace
    return ' '.join(cleaned_title.split()).strip()


class YtdlpLogger:
    """A custom logger to suppress yt-dlp's default output."""
    def debug(self, msg):
        pass
    def warning(self, msg):
        pass
    def error(self, msg):
        pass  # Suppress all errors from yt-dlp during download


def main():
    """
    Main function to orchestrate the download process.
    """
    print("[*] Starting Music Downloader...")
    setup_database()
    
    playlists = get_playlists_from_csv()
    downloaded_ids = get_downloaded_ids()
    
    print(f"[*] Found {len(playlists)} playlists to process.")
    
    for playlist in playlists:
        playlist_id = playlist['id']
        playlist_title = playlist['title']
        playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
        
        print(f"\n[+] Processing Playlist: '{playlist_title}'")
        
        # 1. Get all video info from the playlist without downloading
        try:
            with yt_dlp.YoutubeDL({'extract_flat': True, 'quiet': True}) as ydl:
                playlist_dict = ydl.extract_info(playlist_url, download=False)
                all_videos_in_playlist = playlist_dict.get('entries', [])
        except Exception as e:
            print(f"  └─ [!] Failed to fetch info for this playlist: {e}", file=sys.stderr)
            continue

        # 2. Filter out already downloaded videos
        videos_to_download = [
            video for video in all_videos_in_playlist if video['id'] not in downloaded_ids
        ]
        
        total_in_playlist = len(all_videos_in_playlist)
        total_to_download = len(videos_to_download)
        
        if not videos_to_download:
            print(f"  └─ All {total_in_playlist} songs already downloaded. Skipping.")
            continue
            
        print(f"  └─ Found {total_in_playlist} total songs. Need to download {total_to_download}.")

        # 3. Download the remaining videos
        for i, video_info in enumerate(videos_to_download, 1):
            video_id = video_info['id']
            original_title = video_info.get('title', 'Unknown Title')
            cleaned_title = clean_title(original_title)
            
            # Print the status line without a newline so we can update it
            status_msg = f"    -> ({i}/{total_to_download}) Downloading: {cleaned_title}..."
            sys.stdout.write(status_msg)
            sys.stdout.flush()
            
            # Define output path and yt-dlp options
            output_path = MUSIC_ROOT / playlist_title
            output_template = output_path / f"{cleaned_title}.%(ext)s"

            ydl_opts = {
                'format': 'm4a/bestaudio/best',
                'outtmpl': str(output_template),
                'writethumbnail': True,
                'embedthumbnail': True,
                'embedmetadata': True,
                'postprocessors': [{
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                }, {
                    'key': 'EmbedThumbnail',
                }],
                'postprocessor_args': {
                    'FFmpegMetadata': ['-metadata', f'comment=YouTube Video ID: {video_id}']
                },
                'logger': YtdlpLogger(),
                'quiet': True,
                'no_warnings': True,
                'cookies-from-browser': True
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
                
                # Mark as downloaded in DB only after successful download
                mark_as_downloaded(video_id)
                
                # Update status line to "Done"
                sys.stdout.write(" Done.\n")
                sys.stdout.flush()
                
            except Exception as e:
                # Update status line with error
                sys.stdout.write("\n")
                print(f"      └─ [!] Failed to download '{cleaned_title}': {e}", file=sys.stderr)
                sys.stdout.flush()

    print("\n[+] All playlists processed. Download process complete!")


if __name__ == "__main__":
    main()
