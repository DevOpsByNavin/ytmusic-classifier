# 🎵 YouTube Music AI Categorizer

An intelligent automation tool that uses Google's **Gemini 2.5 Flash AI** to read your "Liked" YouTube videos, figure out their genre/vibe based on the artist and title, and automatically sort them into specific playlists based on your custom descriptions. 

It uses a local **SQLite database** to track progress, meaning you can stop and start the script anytime without losing your work or hitting API limits twice!

---

## 📂 Project Structure

```text
.
├── credentials/
│   ├── client_secret.json       # Your Google Cloud OAuth credentials (YOU PROVIDE THIS)
│   └── token.json               # Auto-generated access token for YouTube API
├── data/
│   ├── music.db                 # SQLite database tracking sorted songs (Auto-created)
│   └── playlists.csv            # The list of your playlists & custom descriptions
├── requirements.txt             # Python dependencies
├── schema/
│   └── database_schema.sql      # The SQL schema for creating the database tables
├── scripts/
│   ├── get_playlist_data.py     # Utility to fetch/create your playlists.csv
│   └── login.py                 # Utility to generate a fresh token.json
└── src/
    ├── ai_matcher.py            # Handles communication with Google Gemini API
    ├── database.py              # Handles saving/reading from SQLite
    ├── main.py                  # The main engine that ties everything together
    └── youtube.py               # Handles the YouTube Data API v3
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
* Python 3.10+ installed on your machine.
* A **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/).
* A `client_secret.json` file from Google Cloud Console (with YouTube Data API v3 enabled).

### 2. Install Dependencies
Open your terminal and install the required Python packages:
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a file named `.env` in the root folder of the project and add your Gemini API key:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

### 4. YouTube Authentication
Place your `client_secret.json` inside the `credentials/` folder. 
Then, run the login script to generate your local access token:
```bash
python scripts/login.py
```
*This will open a browser window asking you to log into your Google Account. Once approved, it generates a `token.json` file.*

### 5. Setup the Database
Ensure your `data/playlists.csv` is populated with your Playlist IDs, Titles, and Descriptions. 
Create your database structure by piping the schema into SQLite:
```bash
sqlite3 data/music.db < schema/database_schema.sql
```

---

## ⚙️ How to Run the App

Once everything is set up, simply run the main script:
```bash
python src/main.py
```

**What the script does:**
1. Loads your playlist descriptions from `playlists.csv` into the database.
2. Fetches up to 100 recent "Liked" videos from your YouTube account.
3. Asks Gemini AI to categorize the new songs (throttled safely to protect rate limits).
4. Connects to YouTube and safely inserts the categorized songs into your target playlists.

---

## ⚠️ Important Edge Cases & Troubleshooting

This project is highly optimized to work around the strict limitations of the Google and YouTube APIs. If you are modifying the code or running into errors, keep these edge cases in mind:

### 1. The YouTube Daily Quota Limit
Google Cloud grants **10,000 API units** per day. 
* Fetching videos is cheap (1 unit). 
* Inserting a video into a playlist costs **50 units**.
* *Edge Case Avoidance:* The script intentionally **does not "unlike"** the videos after moving them, because unliking costs *another* 50 units. By only copying them to the new playlist, we double the amount of songs you can process per day (~200 songs maximum daily). If the script hits the limit, it will safely print a warning and exit. 

### 2. OAuth Token Expiry (`invalid_scope` / Bad Request)
Access tokens expire after 1 hour. The YouTube script is designed to automatically use the "Refresh Token" inside `token.json` to get a new one.
* **The Error:** If you get `google.auth.exceptions.RefreshError: ('invalid_scope: Bad Request')`, it means your token is dead. (This often happens every 7 days if your Google Cloud App is set to "Testing" mode).
* **The Fix:** Simply delete `credentials/token.json` and run `python scripts/login.py` again to generate a fresh one.

### 3. Gemini AI Rate Limits (429 Errors)
The Gemini Free Tier allows a maximum of **10 Requests Per Minute (RPM)**. 
* **The Error:** If you spam the AI too fast, you will receive `429 Quota Exhausted` errors. 
* **The Fix:** In `src/main.py`, the variable `AI_THROTTLE_DELAY = 7` forces the script to wait 7 seconds between every song. This mathematically guarantees you will only make ~8.5 requests per minute, keeping your account perfectly safe.

### 4. Gemini Token Exhaustion & "Search Tools"
Originally, this script allowed the AI to use Google Search to look up obscure songs. However, this causes massive **Tokens Per Minute (TPM)** spikes, triggering long-lasting bans on the free tier. 
* **The Fix:** We rely purely on the AI's internal knowledge and the *Channel Uploader Name* (e.g., "Purna Rai"). The base model is smart enough to categorize 95%+ of indie and regional tracks without needing live web searches. 

### 5. AI Tool Use vs. JSON Mode (400 Errors)
You cannot use Gemini's `response_mime_type="application/json"` simultaneously with external tools. Doing so throws a `400 INVALID_ARGUMENT` error.
* **The Fix:** `ai_matcher.py` explicitly instructs the AI to return *only* the raw Playlist ID string (e.g., `PLIDS4YG...`). We validate the response using standard Python string checks (`result.startswith("PL")`) instead of forcing JSON schema.

---

## 🛠️ Customizing on the Fly
You **do not** need to edit the database manually to change playlist descriptions. 

If the AI is putting songs in the wrong playlist, just open `data/playlists.csv` and tweak the description (e.g., add the word *"Acoustic"* or *"No rap"*). The next time you run `python src/main.py`, the `INSERT OR REPLACE` logic in the database module will instantly update your database with the new AI instructions!