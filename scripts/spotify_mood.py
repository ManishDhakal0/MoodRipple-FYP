# spotify_mood.py
# Fixed: Properly detects Premium, uses desktop app, no browser opening

import os
import time
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import webbrowser

# ===============================
# 🔐 Spotify App Credentials
# ===============================
CLIENT_ID = "ec7d75c8cbe549b48ccb8898a51d7c72"
CLIENT_SECRET = "dd2cae1ec9ba42afa8eccb6f9d335e98"
REDIRECT_URI = "http://127.0.0.1:8888/callback"

# ===============================
# 🎵 Required scopes
# ===============================
SCOPE = (
    "user-read-recently-played "
    "playlist-read-private "
    "user-library-read "
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-top-read "
    "user-read-currently-playing "
    "user-read-private"
)

# ===============================
# File written by face detection
# ===============================
EMOTION_FILE = "latest_emotion.json"

# ===============================
# Emotion -> Mood mapping
# ===============================
EMOTION_TO_MOOD = {
    "happy": "energized",
    "surprise": "energized",
    "neutral": "focused",
    "sad": "calm",
    "fear": "calm",
    "disgust": "calm",
    "angry": "calm",
}

# ===============================
# 🌍 Env vars
# ===============================
os.environ["SPOTIPY_CLIENT_ID"] = CLIENT_ID
os.environ["SPOTIPY_CLIENT_SECRET"] = CLIENT_SECRET
os.environ["SPOTIPY_REDIRECT_URI"] = REDIRECT_URI

# ===============================
# 🔑 Authenticate (force fresh check)
# ===============================
print("=" * 60)
print("🎵 MoodRipple Spotify Controller")
print("=" * 60)
print("\nAuthenticating with Spotify...")

# Delete old cache to force re-check of Premium status
cache_path = "spotify_mood.cache"
if os.path.exists(cache_path):
    print("🔄 Clearing old authentication cache...")
    os.remove(cache_path)

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        scope=SCOPE, cache_path=cache_path, open_browser=True, show_dialog=False
    )
)

print("✅ Authentication successful!")

# Force fresh user info check
user = sp.current_user()
user_name = user.get("display_name", "Unknown")
user_product = user.get("product", "free")

print(f"Logged in as: {user_name}")
print(f"Account type: {user_product.upper()}")

has_premium = user_product == "premium"

if not has_premium:
    print("⚠️ WARNING: Free account detected")
    print("   Spotify Premium is required for app playback control")
    print("   Falling back to browser playback...")
else:
    print("✅ Premium account confirmed!")
    print("   App playback control enabled")


# ===============================
# Helpers
# ===============================
def read_latest_emotion(path: str):
    """
    Returns (emotion, confidence, timestamp_unix) or (None, None, None)
    """
    if not os.path.exists(path):
        return None, None, None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("emotion"), data.get("confidence"), data.get("timestamp_unix")
    except Exception:
        return None, None, None


def get_device_id(spotify: spotipy.Spotify):
    """
    Get device ID - STRONGLY prefer desktop app
    """
    try:
        devices_response = spotify.devices()
        devices = devices_response.get("devices", [])

        if not devices:
            print("⚠️ No Spotify devices found!")
            print("   💡 Please OPEN Spotify desktop app and play any song once")
            return None

        print(f"\n📱 Found {len(devices)} device(s):")
        for i, d in enumerate(devices, 1):
            status = "✅ ACTIVE" if d.get("is_active") else "⚪ inactive"
            print(f"   {i}. {d.get('name')} ({d.get('type')}) - {status}")

        # Priority 1: Desktop/Computer device (even if not active)
        computer_device = next(
            (d for d in devices if d.get("type") == "Computer"), None
        )
        if computer_device:
            device_id = computer_device.get("id")
            print(f"\n✅ Selected: {computer_device.get('name')} (Desktop App)")
            return device_id

        # Priority 2: Any active device
        active = next((d for d in devices if d.get("is_active")), None)
        if active:
            device_id = active.get("id")
            print(f"\n✅ Selected: {active.get('name')} (Active)")
            return device_id

        # Priority 3: First available device
        device = devices[0]
        device_id = device.get("id")
        print(f"\n✅ Selected: {device.get('name')}")
        return device_id

    except Exception as e:
        print(f"⚠️ Error getting device: {e}")
        return None


def get_mood_tracks(spotify: spotipy.Spotify, mood: str, num_tracks=5):
    """
    Get tracks for mood from recent history
    NO recommendations API (avoids 404 errors)
    """
    try:
        print(f"🔍 Getting your recent tracks...")

        # Get recent tracks
        recent = spotify.current_user_recently_played(limit=50)
        tracks = [item["track"] for item in recent.get("items", [])]

        if not tracks:
            # Fallback: top tracks
            print("📊 No recent tracks, using top tracks...")
            top = spotify.current_user_top_tracks(limit=50, time_range="short_term")
            tracks = top.get("items", [])

        if not tracks:
            print("❌ No listening history found")
            return []

        # Remove duplicates and local files
        seen_ids = set()
        unique_tracks = []
        for track in tracks:
            track_id = track.get("id")
            if (
                track_id
                and not track.get("is_local", False)
                and track_id not in seen_ids
            ):
                unique_tracks.append(track)
                seen_ids.add(track_id)

        if not unique_tracks:
            print("❌ No valid tracks found")
            return []

        # Shuffle based on mood (consistent per mood)
        import random

        random.seed(mood)
        shuffled = unique_tracks.copy()
        random.shuffle(shuffled)

        selected = shuffled[:num_tracks]
        print(f"✅ Selected {len(selected)} tracks")

        return selected

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return []


def open_track_in_browser(track_url: str):
    """
    Open track in browser for free users
    """
    print(f"🌐 Opening in browser...")
    webbrowser.open(track_url)


def start_playback_queue(spotify: spotipy.Spotify, device_id: str, track_uris: list):
    """
    Start playback with a queue of tracks (Premium only)
    """
    if not track_uris:
        return False

    try:
        # CRITICAL: Transfer playback to device FIRST
        print(f"🔄 Transferring playback to desktop app...")
        spotify.transfer_playback(device_id=device_id, force_play=False)
        time.sleep(1)  # Give it time to transfer

        # Start playing
        print(f"▶ Starting playback on desktop app...")
        spotify.start_playback(device_id=device_id, uris=track_uris)
        return True

    except spotipy.exceptions.SpotifyException as e:
        error_msg = str(e)

        if "PREMIUM_REQUIRED" in error_msg or "Premium required" in error_msg:
            print(f"⚠️ ERROR: Spotify Premium is required for app playback")
            return False
        elif "NO_ACTIVE_DEVICE" in error_msg:
            print(f"⚠️ ERROR: No active device")
            print(f"   💡 Please open Spotify desktop app!")
            return False
        else:
            print(f"⚠️ Playback failed: {e}")
            return False

    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return False


# ===============================
# MAIN LOOP
# ===============================
print("\n" + "=" * 60)
print("🎛️ AUTO MODE: Waiting for emotion changes...")
print("=" * 60)
print("\n💡 TIPS:")
print("   1. Keep Spotify DESKTOP APP open")
print("   2. Play any song once to activate the app")
print("   3. Let MoodRipple take over from there!\n")
print("Press Ctrl+C to stop.\n")

last_seen_emotion = None

while True:
    try:
        emotion, conf, ts = read_latest_emotion(EMOTION_FILE)

        # Only act when EMOTION CHANGES
        if emotion is not None and emotion != last_seen_emotion:
            last_seen_emotion = emotion

            mood = EMOTION_TO_MOOD.get(emotion, "focused")

            print("\n" + "-" * 60)
            print(f"🧠 EMOTION CHANGED: {emotion.upper()} ({(conf or 0)*100:.1f}%)")
            print(f"🎨 Mood: {mood.upper()}")
            print("-" * 60)

            # Get tracks for this mood
            print(f"\n🎵 Selecting {mood} tracks...")
            track_queue = get_mood_tracks(sp, mood, num_tracks=5)

            if not track_queue:
                print("❌ No tracks found. Please listen to more music on Spotify!")
                time.sleep(2)
                continue

            # Show what we're playing
            print(f"\n📋 Queue ({len(track_queue)} tracks):")
            for i, track in enumerate(track_queue[:3], 1):
                artist = (
                    track["artists"][0]["name"] if track.get("artists") else "Unknown"
                )
                print(f"  {i}. {track['name']} - {artist}")
            if len(track_queue) > 3:
                print(f"  ... and {len(track_queue) - 3} more")

            first_track_url = f"https://open.spotify.com/track/{track_queue[0]['id']}"

            # Try Premium playback, fallback to browser
            if has_premium:
                print(f"\n🎵 Premium account - attempting app playback...")
                device_id = get_device_id(sp)

                if device_id:
                    track_uris = [
                        track["uri"] for track in track_queue if track.get("uri")
                    ]
                    success = start_playback_queue(sp, device_id, track_uris)

                    if success:
                        print("\n✅ SUCCESS! Now playing on your Spotify desktop app!")
                        print("=" * 60)
                    else:
                        print("\n⚠️ App playback failed, opening browser instead")
                        open_track_in_browser(first_track_url)
                        print("=" * 60)
                else:
                    print("\n⚠️ No Spotify device detected")
                    print("💡 Please:")
                    print("   1. Open Spotify desktop app")
                    print("   2. Play any song once")
                    print("   3. Then MoodRipple will control it")
                    print("\n📱 Opening in browser for now...")
                    open_track_in_browser(first_track_url)
                    print("=" * 60)
            else:
                # Free account
                print(f"\n🌐 Free account - opening in browser")
                open_track_in_browser(first_track_url)
                print("=" * 60)

        time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n👋 Stopping MoodRipple Spotify Controller...")
        print("Goodbye!")
        break
    except Exception as e:
        print(f"\n⚠️ Error: {e}")
        time.sleep(1)
