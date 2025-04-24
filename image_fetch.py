"""
image_fetch.py
==============

Enrich Firestore recipe docs with image URLs and upload new CSV rows.

Secrets go in calories.env (or OS env):

GOOGLE_API_KEY=<Google Programmable Search key>
GOOGLE_CX=<Custom Search Engine id>

# EITHER
FIREBASE_CRED=/absolute/path/service-account.json
# OR
FIREBASE_CRED_B64=<base64-encoded contents of service-account.json>

Install deps:
    pip install google-api-python-client firebase-admin pandas python-dotenv
"""

import base64
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build

# ────────────────────────────────────────────────────────────────────────────────
# 1. Load env vars
# ────────────────────────────────────────────────────────────────────────────────
load_dotenv("calories.env")  # ignore if file missing

API_KEY = os.getenv("GOOGLE_API_KEY")
CSE_ID = os.getenv("GOOGLE_CX")
FIREBASE_PATH = os.getenv("FIREBASE_CRED")          # optional
FIREBASE_B64 = os.getenv("FIREBASE_CRED_B64")       # optional

if not API_KEY or not CSE_ID:
    sys.exit("[ERROR] GOOGLE_API_KEY and GOOGLE_CX must be set in calories.env")

if not FIREBASE_PATH and not FIREBASE_B64:
    sys.exit("[ERROR] Provide either FIREBASE_CRED or FIREBASE_CRED_B64")

# Decode Base64 → temp file if that variant is used
if FIREBASE_B64 and not FIREBASE_PATH:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    tmp.write(base64.b64decode(FIREBASE_B64))
    tmp.flush()
    FIREBASE_PATH = tmp.name
    print(f"[INFO] Firebase credentials decoded to {FIREBASE_PATH}")

# Validate credential file
cred_path = Path(FIREBASE_PATH)
if not cred_path.is_file():
    sys.exit(f"[ERROR] Firebase credential file not found at {cred_path}")

with open(cred_path, "r", encoding="utf-8") as f:
    cred_json = json.load(f)
if cred_json.get("type") != "service_account":
    sys.exit("[ERROR] Invalid Firebase JSON: missing \"type\": \"service_account\"")

# ────────────────────────────────────────────────────────────────────────────────
# 2. Firebase setup
# ────────────────────────────────────────────────────────────────────────────────
import firebase_admin
from firebase_admin import credentials, firestore

firebase_admin.initialize_app(credentials.Certificate(str(cred_path)))
db = firestore.client()

# ────────────────────────────────────────────────────────────────────────────────
# 3. Google search helper
# ────────────────────────────────────────────────────────────────────────────────
def google_search_image(query: str) -> str | None:
    """Return first image URL or None.  Raises Exception('QUOTA REACHED') on quota."""
    try:
        service = build("customsearch", "v1", developerKey=API_KEY)
        res = (
            service.cse()
            .list(q=query, cx=CSE_ID, searchType="image", num=1)
            .execute()
        )
        return res["items"][0]["link"] if "items" in res else None
    except Exception as e:
        if "quota" in str(e).lower() or "exceeded" in str(e).lower():
            raise Exception("QUOTA REACHED")
        print(f"[WARN] Google search error for '{query}': {e}")
        return None

# ────────────────────────────────────────────────────────────────────────────────
# 4. Stage 1 – Re-fetch missing images
# ────────────────────────────────────────────────────────────────────────────────
for attempt in range(1, 4):
    print(f"\n[Stage 1] Attempt {attempt}/3")
    missing = list(db.collection("default recipe")
                     .where("image_url", "==", "No image found")
                     .stream())
    if not missing:
        print("[Stage 1] All docs have images.")
        break

    for doc in missing:
        dat = doc.to_dict()
        title = dat.get("title", "")
        try:
            url = google_search_image(title)
        except Exception as e:
            if str(e) == "QUOTA REACHED":
                sys.exit("[ERROR] Google quota reached during re-fetch.")
            url = None

        db.collection("default recipe").document(doc.id).update({
            "image_url": url or "No available photo"
        })
        print(f"  • {title} → {url or 'No available photo'}")
        time.sleep(1)  # polite pause
    time.sleep(2)

# ────────────────────────────────────────────────────────────────────────────────
# 5. Stage 2 – Add new CSV rows
# ────────────────────────────────────────────────────────────────────────────────
try:
    last_doc = next(db.collection("default recipe")
                       .order_by("index", direction=firestore.Query.DESCENDING)
                       .limit(1).stream(), None)
    last_idx = last_doc.to_dict()["index"] if last_doc else -1
except Exception as e:
    print(f"[WARN] Couldn’t fetch last index: {e}")
    last_idx = -1

quota_hit = False
for chunk in pd.read_csv("full_dataset.csv", chunksize=1000):
    for _, row in chunk.iterrows():
        idx = int(row["index"])
        if idx <= last_idx:
            continue

        try:
            img = google_search_image(row["title"])
        except Exception as e:
            if str(e) == "QUOTA REACHED":
                quota_hit = True
                break
            img = None

        doc = {
            "index": idx,
            "title": row["title"],
            "directions": row["directions"],
            "link": row["link"],
            "source": row["source"],
            "NER": row["NER"],
            "image_url": img or "No available photo",
        }
        db.collection("default recipe").add(doc)
        print(f"[Stage 2] Added {idx} – {row['title']}")
    if quota_hit:
        break

print("\n[DONE] Upload stopped (quota)." if quota_hit else "\n[DONE] Upload complete.")
