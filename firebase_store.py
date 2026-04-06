from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def save_session(patient_id, game, started_at, ended_at, score, mistakes, trap_hits, completed, start_level, end_level):
    duration = int((ended_at - started_at).total_seconds())

    db.collection("patients").document(patient_id).collection("sessions").add({
        "game": game,
        "startedAt": started_at,
        "endedAt": ended_at,
        "durationSec": duration,
        "score": score,
        "mistakes": mistakes,
        "trapHits": trap_hits,
        "completed": completed,
        "startLevel": start_level,
        "endLevel": end_level,
        "createdAt": firestore.SERVER_TIMESTAMP
    })


def save_event(patient_id, event_type, game, payload=None):
    db.collection("patients").document(patient_id).collection("events").add({
        "eventType": event_type,
        "game": game,
        "payload": payload or {},
        "createdAt": firestore.SERVER_TIMESTAMP
    })


def update_progress(patient_id, level, play_time):
    ref = db.collection("patients").document(patient_id).collection("progress").document("summary")
    doc = ref.get()

    if doc.exists:
        data = doc.to_dict()
        total_time = data.get("totalPlayTimeSec", 0) + play_time
        sessions = data.get("sessionsCount", 0) + 1
    else:
        total_time = play_time
        sessions = 1

    ref.set({
        "currentLevel": level,
        "totalPlayTimeSec": total_time,
        "sessionsCount": sessions,
        "lastPlayedAt": firestore.SERVER_TIMESTAMP
    }, merge=True)