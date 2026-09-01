import os
import requests
import urllib.parse
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
REDIRECT_URI = f"{BACKEND_URL}/callback"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai.configure(api_key=GEMINI_API_KEY)

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
        
    frontend_redirect = f"{FRONTEND_URL}/processing?code={code}&state={state}"
    return RedirectResponse(frontend_redirect)

@app.get("/generate")
def generate_recommendations(code: str, state: Optional[str] = "balanced"):
    
    token_url = "https://accounts.spotify.com/api/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    token_response = requests.post(token_url, data=data, auth=(CLIENT_ID, CLIENT_SECRET))

    if token_response.status_code != 200:
        return {"error": "Failed at Spotify's token endpoint.", "details": token_response.text}

    token_data = token_response.json()
    access_token = token_data.get("access_token")
    
    if not access_token:
        return {"error": "No access token retrieved."}

    headers = {"Authorization": f"Bearer {access_token}"}
    
    profile_response = requests.get("https://api.spotify.com/v1/me", headers=headers)
    user_name = "Guest" 
    
    if profile_response.status_code == 200 and profile_response.text.strip():
        try:
            user_name = profile_response.json().get("display_name", "Music Lover")
        except Exception as e:
            print(f"Erro ao ler perfil: {e}")
    else:
        print(f"Spotify não mandou o perfil. Status: {profile_response.status_code}")

    artists_response = requests.get("https://api.spotify.com/v1/me/top/artists?limit=7", headers=headers)
    
    if artists_response.status_code != 200 or not artists_response.text.strip():
        print(f"Erro no Spotify Artists: {artists_response.text}")
        return {"recommendations": f"Ops, {user_name}! O Spotify não devolveu seus artistas favoritos agora. Tente novamente mais tarde."}
        
    try:
        top_artists_names = [artist["name"] for artist in artists_response.json().get("items", [])]
    except Exception as e:
        return {"recommendations": "Erro ao interpretar a lista de artistas do Spotify."}

    if not top_artists_names:
         return {"recommendations": f"Oi, {user_name}! Parece que você ainda não tem histórico suficiente no Spotify para analisarmos."}

    artists_string = ", ".join(top_artists_names)

    if state == "hits":
        vibe_instruction = "extremely famous artists, global mainstream hits, and top chart leaders"
    elif state == "underground":
        vibe_instruction = "completely unknown artists, deeply underground indie scene, with very few monthly listeners"
    else:
        vibe_instruction = "a balanced mix of somewhat known and emerging artists"

    prompt = (
        f"Act as a music curator focused on discovering talent. "
        f"The user is named {user_name}. Their favorite artists are: {artists_string}. "
        f"Recommend 5 artists that are {vibe_instruction} that they will likely love based on this taste. "
        f"Return ONLY the text in this exact format (no introductions or conclusions):\n"
        f"Based on your taste, {user_name}, these artists match your vibe:\n\n"
        f"1. [Artist Name]: [One sentence description]\n"
        f"2. [Artist Name]: [One sentence description]..."
    )

    try:
        model = genai.GenerativeModel('gemini-pro') 
        ia_response = model.generate_content(prompt)
        recommendation_text = ia_response.text
    except Exception as e:
        print(f"Erro do Gemini: {e}") 
        recommendation_text = f"Based on your taste, {user_name}, we couldn't load the recommendations right now. Please try again!"

    return {"recommendations": recommendation_text}