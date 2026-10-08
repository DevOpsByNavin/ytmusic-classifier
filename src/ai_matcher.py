import os
import sys
import time
from google import genai
from google.genai import types

# --- CONFIGURABLE VARIABLES ---
MODEL_NAME = "gemini-2.5-flash"  

# --- GLOBAL STATE FOR KEY ROTATION ---
API_KEYS = []
current_key_index = 0
client = None

def _load_api_keys():
    """
    Dynamically loads all API keys from the environment that start with 'GEMINI_API_KEY'.
    """
    global API_KEYS
    API_KEYS = [val for key, val in os.environ.items() if key.startswith("GEMINI_API_KEY")]
    
    # Remove any potential duplicates
    API_KEYS = list(set(API_KEYS))
    
    if not API_KEYS:
        print("[-] No API keys found. Please define variables starting with 'GEMINI_API_KEY' in your .env file.")
        sys.exit(1)
        
    print(f"[+] Successfully loaded {len(API_KEYS)} API key(s) for rotation.")

def setup_ai():
    """
    Initializes the AI client with the current API key in the rotation.
    Automatically loads keys on first run to maintain backward compatibility.
    """
    global client, current_key_index
    
    # Load keys on first run if not already loaded
    if not API_KEYS:
        _load_api_keys()

    if current_key_index >= len(API_KEYS):
        print("\n[!] All API keys have hit their limits. Exiting to protect API quotas.")
        sys.exit(1)
        
    api_key = API_KEYS[current_key_index]
    client = genai.Client(api_key=api_key)

def categorize_song(title, channel, playlists):
    """
    Asks Gemini to match the song to a playlist.
    Uses Google Search tool if it doesn't recognize the song immediately.
    Rotates API keys automatically upon rate limit errors.
    """
    # Global declaration MUST be at the top of the function to avoid SyntaxError
    global current_key_index
    
    playlist_context = "\n".join([f"ID: {p['id']} | Title: {p['title']} | Desc: {p['description']}" for p in playlists])
    
    prompt = f"""
    You are an expert music curator. Match the following song to ONE of the provided playlists.
    If you are unsure of the genre, use the Google Search tool to look up the song/artist.
    If it fits absolutely nowhere, use the Uncategorized playlist ID.
    
    Playlists:
    {playlist_context}
    
    Song Title: "{title}"
    Uploader/Artist: "{channel}"
    
    Return ONLY the raw playlist ID string (e.g., PLIDS4YGbfD...) and absolutely nothing else. Do not use markdown.
    """

    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )

    # Max attempts is now based on the number of available keys
    max_attempts = len(API_KEYS)
    
    for attempt in range(max_attempts):
        try:
            # Ensure the client is initialized with the current (or newly rotated) key
            setup_ai()
            
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config
            )
            
            # Clean up any potential whitespace or markdown the AI might accidentally add
            result = response.text.strip().replace("```", "").strip()
            
            # Validate that the AI actually returned a Playlist ID
            if result.startswith("PL") and len(result) > 10:
                return result
            else:
                print(f"\n[-] AI returned an invalid format: {result}")
                return None
                
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
                print(f"\n[!] AI Rate limit hit on current key. Rotating to next API key...")
                
                # Rotate to the next key
                current_key_index += 1
                
                if current_key_index >= len(API_KEYS):
                    print("\n[!] All API keys have hit their limits. Exiting to protect API quotas.")
                    sys.exit(1)
                    
                # Loop continues, setup_ai() will be called at the top of the next iteration with the new key
                
            else:
                print(f"\n[-] Unexpected AI Error for '{title}': {e}")
                return None
                
    print("\n[!] AI Rate limits maxed out across all keys. Exiting to protect API quotas.")
    sys.exit(1)