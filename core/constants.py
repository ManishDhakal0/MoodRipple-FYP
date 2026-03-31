# core/constants.py
# All app-wide constants in one place

# ── Spotify ──────────────────────────────────────────────────
SPOTIFY_CLIENT_ID     = "ec7d75c8cbe549b48ccb8898a51d7c72"
SPOTIFY_CLIENT_SECRET = "dd2cae1ec9ba42afa8eccb6f9d335e98"
SPOTIFY_REDIRECT_URI  = "http://127.0.0.1:8888/callback"
SPOTIFY_SCOPE = (
    "user-read-recently-played "
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing "
    "user-top-read "
    "user-read-private "
    "user-read-email"
)
SPOTIFY_CACHE_PATH = "spotify_mood.cache"

# ── Google Calendar ───────────────────────────────────────────
GOOGLE_TOKEN_PATH       = "token.pickle"
GOOGLE_CREDENTIALS_PATH = "credentials.json"
GOOGLE_SCOPES           = ["https://www.googleapis.com/auth/calendar"]

# ── Emotion / mood ────────────────────────────────────────────
EMOTION_FILE = "latest_emotion.json"

EMOTION_TO_MOOD = {
    "happy":   "energized",
    "surprise":"energized",
    "neutral": "focused",
    "sad":     "calm",
    "fear":    "calm",
    "disgust": "calm",
    "angry":   "calm",
    "drowsy":  "energized",  # upbeat music to wake you up
}

EMOTION_EMOJIS = {
    "angry":   "😠",
    "disgust": "🤢",
    "fear":    "😨",
    "happy":   "😊",
    "neutral": "😐",
    "sad":     "😢",
    "surprise":"😮",
}

MOOD_ICONS = {
    "energized": "⚡",
    "focused":   "🎯",
    "calm":      "🌊",
    "drowsy":    "😴",
}

REACTION_MAP = {
    "angry":   "Take a breath — calming vibe incoming.",
    "disgust": "Let's switch things up.",
    "fear":    "You seem tense. Calmer sounds coming.",
    "happy":   "Great energy! Keeping it up.",
    "neutral": "Steady mood. Balanced vibe.",
    "sad":     "It's okay. Lifting things gently.",
    "surprise":"Something caught your attention!",
}

# ── Model paths ───────────────────────────────────────────────
MODEL_PATH       = "emotion_recognition_model_auto.h5"
MODEL_FALLBACK   = "emotion_model_final.h5"
CLASS_NAMES_PATH = "class_names.json"
DEFAULT_LABELS   = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

# ── Detection settings ────────────────────────────────────────
EXPORT_INTERVAL_SEC  = 30
VOTE_WINDOW_SEC      = 6
MIN_FACE_CONFIDENCE  = 0.38
MIN_STABLE_CONFIDENCE= 0.50

EMOTION_GROUPS = {
    "happy":   {"happy": 1.0,  "surprise": 0.55},
    "sad":     {"sad": 1.0,    "fear": 0.45, "disgust": 0.20},
    "neutral": {"neutral": 0.82,"angry": 0.18,"disgust": 0.10},
}
