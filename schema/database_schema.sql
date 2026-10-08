-- Table 1: Stores your playlists and their context
CREATE TABLE IF NOT EXISTS playlists (
    playlist_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT
);

-- Table 2: Stores the liked videos and tracks their progress
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    channel_name TEXT,
    url TEXT,
    
    -- Where the AI decided to put it
    assigned_playlist_id TEXT, 
    
    -- Progress Tracking
    is_categorized INTEGER DEFAULT 0,  -- 1 when AI has assigned a playlist
    is_synced INTEGER DEFAULT 0,       -- 1 when YouTube API has successfully added it to the playlist
    
    FOREIGN KEY(assigned_playlist_id) REFERENCES playlists(playlist_id)
);