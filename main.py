import os
import requests
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

app = FastAPI()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

REDIRECT_URI = "http://127.0.0.1:8000/callback" 

@app.get("/")
def home():
    return {"message": "Welcome to TuneMind! Access /login to start."}

@app.get("/login")
def login_spotify():
    scopes = "user-top-read" 
    
    auth_url = (
        f"https://accounts.spotify.com/authorize?"
        f"client_id={CLIENT_ID}&response_type=code&"
        f"redirect_uri={REDIRECT_URI}&scope={scopes}"
    )
    
    return RedirectResponse(auth_url)

@app.get("/callback")
def spotify_callback(code: Optional[str] = None, error: Optional[str] = None):
    if error:
        return {"error": "Spotify blocked the access.", "details": error}
    
    if not code:
        return {"error": "Authorization code not found."}
        
    token_url = "https://accounts.spotify.com/api/token"
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    token_response = requests.post(token_url, data=data, auth=(CLIENT_ID, CLIENT_SECRET))

    if token_response.status_code != 200:
        return {"error": "Failed at Spotify's token endpoint.", "details": token_response.json()}

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    top_artists_url = "https://api.spotify.com/v1/me/top/artists"

    artists_response = requests.get(top_artists_url, headers=headers)
    artists_data = artists_response.json()

    top_artists_names = [artist["name"] for artist in artists_data.get("items", [])]

    top_tracks_url = "https://api.spotify.com/v1/me/top/tracks"

    tracks_response = requests.get(top_tracks_url, headers=headers)
    tracks_data = tracks_response.json()

    top_tracks_names = [track["name"] for track in tracks_data.get("items", [])]

    #MOCK TEST
    roast_text = (
        f"You listen to a lot of {top_artists_names[0] if top_artists_names else 'nothing'}! "
    )

    return {
        "message": "Welcome to TuneMind!",
        "top_artists": top_artists_names,
        "full_artists_data": artists_data,
        "top_tracks": top_tracks_names,
        "full_tracks_data": tracks_data,
        "ai_roast": roast_text
    }