import os
import requests
import urllib.parse
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

app = FastAPI()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

genai.configure(api_key=GEMINI_API_KEY)

REDIRECT_URI = "http://127.0.0.1:8000/callback" 

@app.get("/")
def home():
    return {"message": "Welcome to TuneMind! Access /login to start."}

@app.get("/login")
def login_spotify(filter: str = "balanced"):
    scopes = "user-top-read user-read-private" 
    
    auth_url = (
        f"https://accounts.spotify.com/authorize?"
        f"client_id={CLIENT_ID}&response_type=code&"
        f"redirect_uri={REDIRECT_URI}&scope={scopes}&state={filter}"
    )
    
    return RedirectResponse(auth_url)

@app.get("/callback")
def spotify_callback(code: Optional[str] = None, error: Optional[str] = None, state: Optional[str] = None):
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
    headers = {"Authorization": f"Bearer {access_token}"}
    
    profile_response = requests.get("https://api.spotify.com/v1/me", headers=headers)
    profile_data = profile_response.json()
    user_name = profile_data.get("display_name", "Music Lover")

    artists_response = requests.get("https://api.spotify.com/v1/me/top/artists?limit=7", headers=headers)
    top_artists_names = [artist["name"] for artist in artists_response.json().get("items", [])]

    if state == "hits":
        vibe_instruction = "extremely famous artists, global mainstream hits, and top chart leaders"
    elif state == "underground":
        vibe_instruction = "completely unknown artists, deeply underground indie scene, with very few monthly listeners"
    else:
        vibe_instruction = "a balanced mix of somewhat known and emerging artists"

    prompt = (
        f"Act as a music curator focused on discovering talent. "
        f"The user is named {user_name}. Their favorite artists are: {', '.join(top_artists_names)}. "
        f"Recommend 5 artists that are {vibe_instruction} that they will likely love based on this taste. "
        f"Return ONLY the text in this exact format (no introductions or conclusions):\n"
        f"Based on your taste, {user_name}, these artists match your vibe:\n\n"
        f"1. [Artist Name]: [One sentence description]\n"
        f"2. [Artist Name]: [One sentence description]..."
    )

    try:
        model = genai.GenerativeModel('gemini-3.6-flash')
        ia_response = model.generate_content(prompt)
        recommendation_text = ia_response.text
    except Exception as e:
        print(f"error: {e}") 
        recommendation_text = f"Based on your taste, {user_name}, we couldn't load the recommendations right now. Please try again!"

    safe_parameters = urllib.parse.urlencode({
        "recommendations": recommendation_text
    })
    
    frontend_url = f"http://localhost:3000/results?{safe_parameters}"
    
    return RedirectResponse(frontend_url)