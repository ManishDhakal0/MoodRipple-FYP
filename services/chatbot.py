# services/chatbot.py
# MoodBot — rule-based intent engine for music control + mood feedback.

import re
import json
import random
import os
from dataclasses import dataclass, field
from typing import Optional, Any


_PREFS_FILE = "music_prefs.json"


@dataclass
class BotResponse:
    text: str
    action: Optional[str] = None   # "skip","prev","pause","play","volume",
                                    # "set_language","set_source","set_mood"
    value: Any = None


# ── Intent patterns (checked in order) ────────────────────────────────────────
_INTENTS = [
    # Music control
    ("skip",        r"\b(skip|next|next song|change (this )?song|skip (this|it))\b"),
    ("prev",        r"\b(previous|prev|go back|last song|back)\b"),
    ("pause",       r"\b(pause|stop( the music)?|mute)\b"),
    ("play",        r"\b(play|resume|unpause|start( music)?|continue)\b"),
    ("vol_up",      r"\b(louder|volume up|turn (it )?up|more volume|increase volume|too quiet)\b"),
    ("vol_down",    r"\b(quieter|softer|volume down|turn (it )?down|lower( volume)?|too loud)\b"),
    ("set_vol",     r"(set )?volume (to )?(\d+)"),

    # Mood override
    ("energized",   r"\b(energize( me)?|hype( me up)?|pump (me )?up|upbeat|party( music)?|happy music|give me energy|i('m| am) hype)\b"),
    ("focused",     r"\b(focus( me)?|concentrate|study( music)?|work( music)?|productive|help me focus)\b"),
    ("calm",        r"\b(calm( me down)?|relax|chill( out)?|stress(ed)?|help me (sleep|relax|calm)|soothe|sad music|peaceful)\b"),
    ("drowsy",      r"\b(sleepy|drowsy|tired|wake me up|i('m| am) tired)\b"),

    # Query current state
    ("query_mood",  r"\b(how am i( feeling)?|what('?s| is) my (mood|emotion)|my (mood|emotion)|how (do i|i) feel)\b"),
    ("query_track", r"\b(what('?s| is) (playing|on)|current (song|track)|what song)\b"),

    # Language / genre
    ("lang_lofi",      r"\b(lofi|lo.fi)\b"),
    ("lang_kpop",      r"\b(kpop|k.pop|korean( music)?)\b"),
    ("lang_hindi",     r"\b(hindi( music| song)?)\b"),
    ("lang_bollywood", r"\b(bollywood)\b"),
    ("lang_nepali",    r"\b(nepali( music| song)?)\b"),
    ("lang_english",   r"\b(english( music| song)?|western( music)?)\b"),
    ("lang_party",     r"\b(party (music|songs|playlist))\b"),
    ("lang_classical", r"\b(classical( music)?)\b"),
    ("lang_all",       r"\b(all (genres?|languages?|music)|mix (it )?up|anything)\b"),

    # Source
    ("src_discover",   r"\b(discover|new music|something new|surprise me|fresh( tracks)?|recommend)\b"),
    ("src_favourites", r"\b(favourites?|favorites?|my (music|songs?|playlist)|personal)\b"),
    ("src_mix",        r"\b(mix( it up)?|blend|both)\b"),

    # Meta
    ("greeting",    r"^(hi|hello|hey|sup|yo|what'?s up|howdy)\b"),
    ("help",        r"\b(help|commands|what can you do|options|list commands)\b"),
    ("thanks",      r"\b(thanks?|thank you|cheers|great|awesome|nice)\b"),
    ("feedback",    r"\b(how('?s| is) (it going|everything)|rate my mood|analyze me|what do you think)\b"),
]

_COMPILED = [(name, re.compile(pat, re.IGNORECASE)) for name, pat in _INTENTS]

# ── Response templates ─────────────────────────────────────────────────────────
_R = {
    "skip": [
        "Skipping to the next track! ⏭",
        "On to the next one! ⏭",
        "Skipped! Hope you like the next song 🎵",
    ],
    "prev": [
        "Going back to the previous track ⏮",
        "Back to the last song! ⏮",
    ],
    "pause": [
        "Music paused ⏸",
        "Paused! Take your time.",
        "Music on hold ⏸",
    ],
    "play": [
        "Resuming playback ▶",
        "Let's go! Music back on ▶",
        "Playing! 🎵",
    ],
    "vol_up": [
        "Turning it up! 🔊",
        "Volume increased 🔊",
        "Louder it is! 🔊",
    ],
    "vol_down": [
        "Bringing it down a notch 🔉",
        "Volume reduced 🔉",
        "Quieter, got it 🔉",
    ],
    "thanks": [
        "Anytime! 😊",
        "Happy to help! 🎵",
        "You're welcome!",
        "Always here for you 🤝",
    ],
    "no_spotify": [
        "You'll need to connect Spotify first — head to the Spotify page!",
        "Spotify isn't connected yet. Connect it from the sidebar 🎵",
    ],
    "unknown": [
        "Hmm, I didn't quite catch that. Try 'help' to see what I can do!",
        "Not sure what you mean — type 'help' for a list of commands.",
        "I didn't understand that. Type 'help' to see all commands 💬",
    ],
}

_MOOD_MESSAGES = {
    "energized": [
        "You're full of energy today! 🔥 Queuing upbeat tracks to match!",
        "High energy detected! ⚡ Playing something hype for you!",
        "Feeling energized! 🎉 Let's keep that momentum going!",
    ],
    "focused": [
        "Focus mode on! 🎯 Playing smooth tracks to keep you in the zone.",
        "You look focused — cueing up some concentration music 🎧",
        "Deep work mode engaged 🎯 Music will stay calm and steady.",
    ],
    "calm": [
        "Feeling calm? 🌊 I'll keep the music mellow and soothing.",
        "You seem relaxed — keeping the vibes peaceful 🌙",
        "Calm detected 🌿 Playing something soft and easy.",
    ],
    "drowsy": [
        "Looks like you need a pick-me-up! ⚡ Switching to something energizing!",
        "Don't fall asleep on me! ☕ Queuing some lively tracks.",
        "Drowsiness detected 😴 Let me wake you up with some energy!",
    ],
}

_EMOTION_MESSAGES = {
    "happy": [
        "You're looking happy! 😄 Great energy — keeping the vibes high!",
        "That smile is contagious! 😊 I'll queue something fun to match your mood!",
        "Happy detected! 🎉 Let's celebrate with some upbeat tracks!",
        "You seem to be in a great mood today! 🌟 Music to match incoming!",
    ],
    "sad": [
        "Hey, it looks like you might be feeling a bit down. 💙 I've got some soothing music for you.",
        "Rough day? 🌧 I'll keep things gentle and calming. You've got this.",
        "Feeling a little sad — that's okay. 🌊 Let me put on something soft and comforting.",
        "I notice you seem down. 💜 Music can help — switching to calming tracks.",
    ],
    "angry": [
        "Take a breath — calming vibes are on the way. 🌿",
        "Feeling frustrated? 😤 Let me switch to something mellow to help you unwind.",
        "I see some tension! 🧘 Switching to relaxing music to help ease the mood.",
        "Hey, let's take it down a notch. 🌊 Calm music incoming.",
    ],
    "fear": [
        "You seem a little stressed. 🤍 I'll keep things calm and steady for you.",
        "Everything's okay! 🕊 Let me play something peaceful to ease your mind.",
        "Feeling anxious? 🌿 Soft, soothing music on the way.",
    ],
    "disgust": [
        "Not vibing with something? 😅 Let me switch up the music!",
        "Let's change the energy! 🎵 Queuing something fresh for you.",
        "Switching things up — new tracks incoming! 🔄",
    ],
    "surprise": [
        "Whoa, something surprised you! 😲 Keeping the energy alive!",
        "Surprised? 🎉 I'll match that energy with something exciting!",
        "Something caught you off guard! ⚡ Let's keep the momentum going!",
    ],
    "neutral": [
        "Steady and focused — I'll keep things smooth 🎯",
        "Calm and collected! 🎧 Focus music playing in the background.",
        "In the zone? 📚 I'll keep things steady so you can concentrate.",
    ],
    "drowsy": [
        "Hey, don't doze off on me! ☕ Switching to something to wake you up!",
        "Drowsiness detected 😴 — time for some energizing beats!",
        "You look sleepy! ⚡ Let me play something lively to keep you going!",
        "Wake up! ☕ High-energy tracks coming your way!",
    ],
}

_HELP_TEXT = (
    "Here's what I can do for you:\n\n"
    "🎵  Music control:\n"
    "  • 'skip' or 'next' — skip track\n"
    "  • 'pause' / 'play' — toggle playback\n"
    "  • 'louder' / 'quieter' — adjust volume\n"
    "  • 'volume 60' — set exact volume\n\n"
    "🎭  Mood control:\n"
    "  • 'give me energy' — switch to energized music\n"
    "  • 'calm me down' — switch to calm music\n"
    "  • 'help me focus' — switch to focused music\n\n"
    "🎸  Change genre:\n"
    "  • 'play lofi', 'play kpop', 'play hindi'\n"
    "  • 'surprise me' — discover new music\n"
    "  • 'my favourites' — personal playlist\n\n"
    "📊  Info:\n"
    "  • 'how am I feeling?' — current mood\n"
    "  • 'what's playing?' — current track"
)


# ── Language/source maps ───────────────────────────────────────────────────────
_LANG_MAP = {
    "lang_lofi":      ("lofi",      "Lo-fi"),
    "lang_kpop":      ("kpop",      "K-Pop"),
    "lang_hindi":     ("hindi",     "Hindi"),
    "lang_bollywood": ("bollywood", "Bollywood"),
    "lang_nepali":    ("nepali",    "Nepali"),
    "lang_english":   ("english",   "English"),
    "lang_party":     ("party",     "Party"),
    "lang_classical": ("classical", "Classical"),
    "lang_all":       ("all",       "All genres"),
}
_SRC_MAP = {
    "src_discover":   ("discover",   "Discover mode — fresh recommendations"),
    "src_favourites": ("favourites", "Your favourites playlist"),
    "src_mix":        ("mix",        "Smart mix of old and new"),
}
_MOOD_MAP = {
    "energized": "energized",
    "focused":   "focused",
    "calm":      "calm",
    "drowsy":    "energized",   # drowsy → flip to energized to wake up
}


# ── Main engine ───────────────────────────────────────────────────────────────
class MoodBot:
    """Rule-based chatbot for music control and mood feedback."""

    def process(self, text: str, context: dict) -> BotResponse:
        t = text.strip()
        if not t:
            return BotResponse("Say something! Type 'help' to see what I can do.")

        t_lower = t.lower()
        spotify_ok = context.get("spotify_connected", False)
        is_playing = context.get("is_playing", False)
        volume     = context.get("volume", 50)
        mood       = context.get("current_mood") or "unknown"
        emotion    = context.get("current_emotion") or "unknown"
        track      = context.get("current_track") or "nothing"
        artist     = context.get("current_artist") or ""
        language   = context.get("language", "all")
        source     = context.get("source", "mix")

        for intent, pattern in _COMPILED:
            m = pattern.search(t_lower)
            if not m:
                continue

            # ── Music control (requires Spotify) ──────────────────────────
            if intent == "skip":
                if not spotify_ok:
                    return BotResponse(random.choice(_R["no_spotify"]))
                return BotResponse(random.choice(_R["skip"]), action="skip")

            if intent == "prev":
                if not spotify_ok:
                    return BotResponse(random.choice(_R["no_spotify"]))
                return BotResponse(random.choice(_R["prev"]), action="prev")

            if intent == "pause":
                if not spotify_ok:
                    return BotResponse(random.choice(_R["no_spotify"]))
                if not is_playing:
                    return BotResponse("Music is already paused!")
                return BotResponse(random.choice(_R["pause"]), action="pause")

            if intent == "play":
                if not spotify_ok:
                    return BotResponse(random.choice(_R["no_spotify"]))
                if is_playing:
                    return BotResponse("Music is already playing!")
                return BotResponse(random.choice(_R["play"]), action="play")

            if intent == "vol_up":
                if not spotify_ok:
                    return BotResponse(random.choice(_R["no_spotify"]))
                new_vol = min(100, volume + 15)
                return BotResponse(
                    f"{random.choice(_R['vol_up'])} (Volume → {new_vol}%)",
                    action="volume", value=new_vol)

            if intent == "vol_down":
                if not spotify_ok:
                    return BotResponse(random.choice(_R["no_spotify"]))
                new_vol = max(0, volume - 15)
                return BotResponse(
                    f"{random.choice(_R['vol_down'])} (Volume → {new_vol}%)",
                    action="volume", value=new_vol)

            if intent == "set_vol":
                if not spotify_ok:
                    return BotResponse(random.choice(_R["no_spotify"]))
                try:
                    val = int(m.group(3))
                    val = max(0, min(100, val))
                    return BotResponse(
                        f"Volume set to {val}% 🔊",
                        action="volume", value=val)
                except (IndexError, ValueError):
                    pass

            # ── Mood override ─────────────────────────────────────────────
            if intent in ("energized", "focused", "calm"):
                target = intent
                if not spotify_ok:
                    return BotResponse(
                        f"Noted — you want {target} music! Connect Spotify to make it happen 🎵")
                label = target.capitalize()
                return BotResponse(
                    f"Switching to {label} music for you! {_mood_icon(target)}",
                    action="set_mood", value=target)

            if intent == "drowsy":
                # Wake them up with energized
                if not spotify_ok:
                    return BotResponse("Connect Spotify and I'll wake you up with some energy! ⚡")
                return BotResponse(
                    "Time to wake up! ⚡ Switching to something high-energy!",
                    action="set_mood", value="energized")

            # ── Query current state ───────────────────────────────────────
            if intent == "query_mood":
                mood_desc = _mood_description(mood)
                emo_str = f" (detecting: {emotion})" if emotion not in ("unknown", mood) else ""
                return BotResponse(
                    f"Right now you seem {mood_desc}{emo_str}.\n"
                    f"Music is set to {mood.capitalize()} mode 🎭")

            if intent == "query_track":
                if not spotify_ok:
                    return BotResponse("Connect Spotify to see what's playing!")
                if track == "nothing" or not track:
                    return BotResponse("Nothing is playing right now.")
                by = f" by {artist}" if artist else ""
                return BotResponse(f"Now playing: {track}{by} 🎵")

            # ── Language / genre ──────────────────────────────────────────
            if intent in _LANG_MAP:
                key, label = _LANG_MAP[intent]
                return BotResponse(
                    f"Switching to {label} music! 🎸 This applies to your next autoplay session.",
                    action="set_language", value=key)

            # ── Source ────────────────────────────────────────────────────
            if intent in _SRC_MAP:
                key, label = _SRC_MAP[intent]
                return BotResponse(
                    f"Music source set to: {label} 🎯",
                    action="set_source", value=key)

            # ── Meta ──────────────────────────────────────────────────────
            if intent == "greeting":
                status = f"Currently playing {track}." if spotify_ok and track != "nothing" else "Spotify isn't connected yet."
                return BotResponse(
                    f"Hey! 👋 I'm MoodBot — your emotion-aware music assistant.\n{status}\nType 'help' to see what I can do!")

            if intent == "help":
                return BotResponse(_HELP_TEXT)

            if intent == "thanks":
                return BotResponse(random.choice(_R["thanks"]))

            if intent == "feedback":
                conf = context.get("confidence", 0)
                conf_str = f" ({conf*100:.0f}% confidence)" if conf else ""
                return BotResponse(
                    f"Based on your face, I'm detecting: {emotion}{conf_str}\n"
                    f"Overall mood: {mood.capitalize()} {_mood_icon(mood)}\n"
                    f"Language filter: {language.capitalize()} | Source: {source.capitalize()}")

        # ── No intent matched ─────────────────────────────────────────────
        return BotResponse(random.choice(_R["unknown"]))

    def mood_message(self, mood: str) -> str:
        """Returns a proactive message for when detected mood changes."""
        msgs = _MOOD_MESSAGES.get(mood, [])
        return random.choice(msgs) if msgs else f"Mood detected: {mood.capitalize()} {_mood_icon(mood)}"

    def emotion_message(self, emotion: str, mood: str) -> str:
        """Returns a proactive message keyed by raw emotion (happy/sad/angry…)."""
        msgs = _EMOTION_MESSAGES.get(emotion.lower(), [])
        if msgs:
            return random.choice(msgs)
        return self.mood_message(mood)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _mood_icon(mood: str) -> str:
    return {"energized": "⚡", "focused": "🎯", "calm": "🌊", "drowsy": "😴"}.get(mood, "🎭")


def _mood_description(mood: str) -> str:
    return {
        "energized": "energized and upbeat 🔥",
        "focused":   "focused and in the zone 🎯",
        "calm":      "calm and relaxed 🌊",
        "drowsy":    "a bit drowsy 😴",
    }.get(mood, f"{mood}")


def load_prefs() -> dict:
    try:
        with open(_PREFS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"source": "mix", "language": "all"}


def save_prefs(prefs: dict):
    try:
        with open(_PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
    except Exception:
        pass
