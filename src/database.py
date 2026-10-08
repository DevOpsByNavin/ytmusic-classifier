import sqlite3
import csv
import os

# --- CONFIGURABLE VARIABLES ---
DB_PATH = os.path.join("data", "music.db")
CSV_PATH = os.path.join("data", "playlists.csv")

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_playlists_from_csv():
    """Reads the CSV and populates the playlists table."""
    if not os.path.exists(CSV_PATH):
        print(f"[-] CSV file not found at {CSV_PATH}. Make sure get_playlist_data.py ran.")
        return
    
    with get_connection() as conn:
        cursor = conn.cursor()
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute("""
                    INSERT OR REPLACE INTO playlists (playlist_id, title, description)
                    VALUES (?, ?, ?)
                """, (row['Playlist ID'], row['Title'], row['Description']))
        conn.commit()

def get_all_playlists():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT playlist_id, title, description FROM playlists")
        return [{"id": row[0], "title": row[1], "description": row[2]} for row in cursor.fetchall()]

def insert_liked_video(video_id, title, channel_name, url):
    """Inserts a liked video into the database.
    
    Returns True if the video was newly inserted, False if it already existed.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO videos (video_id, title, channel_name, url)
            VALUES (?, ?, ?, ?)
        """, (video_id, title, channel_name, url))
        conn.commit()
        # If rowcount is 1, the row was inserted (new video). If 0, it was ignored (duplicate).
        return cursor.rowcount == 1

def get_uncategorized_videos(limit=50):
    """Gets videos from the DB that haven't been categorized yet."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT video_id, title, channel_name FROM videos WHERE is_categorized = 0"
    params = []
    
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
        
    cursor.execute(query, params)
    videos = cursor.fetchall()
    conn.close()
    return videos

def update_video_category(video_id, playlist_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE videos SET assigned_playlist_id = ?, is_categorized = 1 WHERE video_id = ?
        """, (playlist_id, video_id))
        conn.commit()

def get_unsynced_videos(limit=50):
    """Gets categorized videos that haven't been synced to a YT playlist yet."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT video_id, assigned_playlist_id FROM videos WHERE is_categorized = 1 AND is_synced = 0"
    params = []

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    cursor.execute(query, params)
    videos = cursor.fetchall()
    conn.close()
    return videos

def mark_video_synced(video_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE videos SET is_synced = 1 WHERE video_id = ?", (video_id,))
        conn.commit()