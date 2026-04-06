import os
import time
from datetime import datetime

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except Exception:
    firebase_admin = None
    credentials = None
    firestore = None


SERVICE_ACCOUNT_FILE = "serviceAccountKey.json"
PATIENT_ID = "p001"


class FirebaseLogger:
    def __init__(self):
        self.enabled = False
        self.session_id = f"sess_{int(time.time() * 1000)}"
        self.active_game = ""
        self.active_start_ms = 0
        self.db = None

        if firebase_admin is None:
            print("firebase-admin орнатылмаған.")
            return

        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            print("serviceAccountKey.json табылмады.")
            return

        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
                firebase_admin.initialize_app(cred)

            self.db = firestore.client()
            self.enabled = True
            print("Firestore қосылды.")
        except Exception as e:
            print("Firestore init қатесі:", e)
            self.enabled = False

    def _now_text(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _events_ref(self):
        return (
            self.db.collection("patients")
            .document(PATIENT_ID)
            .collection("events")
        )

    def log_event(self, event_type, game="APP", duration_sec=0, extra=None):
        if not self.enabled:
            return

        payload = {
            "sessionId": self.session_id,
            "eventType": event_type,
            "game": game,
            "timeMs": int(time.time() * 1000),
            "timeText": self._now_text(),
            "durationSec": int(duration_sec),
        }

        if extra and isinstance(extra, dict):
            payload.update(extra)

        try:
            self._events_ref().add(payload)
        except Exception as e:
            print("Firestore write қатесі:", e)

    def app_open(self):
        self.log_event("app_open", "APP", 0)

    def app_close(self):
        self.end_game("app_close")
        self.log_event("app_close", "APP", 0)

    def start_game(self, game_name):
        if self.active_game:
            self.end_game("switch_game")

        self.active_game = game_name
        self.active_start_ms = int(time.time() * 1000)
        self.log_event("game_start", game_name, 0)

    def end_game(self, reason="menu"):
        if not self.active_game:
            return

        now_ms = int(time.time() * 1000)
        duration_sec = max(0, (now_ms - self.active_start_ms) // 1000)

        self.log_event(
            "game_end",
            self.active_game,
            duration_sec,
            {"reason": reason}
        )

        self.active_game = ""
        self.active_start_ms = 0

    def save_score(self, game_name, score):
        self.log_event(
            "score_save",
            game_name,
            0,
            {"score": int(score)}
        )