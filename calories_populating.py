# ── calories.py ──────────────────────────────────────────────────────────
"""
Adds `calories` and `cooking_time` (minutes) to every document
in the "default recipe" Firestore collection.

Deps ── pip install openai>=1.3.7 firebase-admin tqdm python-dotenv
Secrets
  • Service-account JSON  (hard-coded path below)
  • OPENAI_API_KEY in .env   OR   exported in the shell
"""

import os, json, time, logging, sys
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from openai import OpenAI, RateLimitError, APIError

# ─── CONFIG ──────────────────────────────────────────────────────────────
SERVICE_KEY   = Path(r"PATH TO FIREBASE JSON CONFIG FILE")
COLLECTION    = "default recipe"
MODEL         = "gpt-4o-mini"          # or gpt-3.5-turbo
TEMPERATURE   = 0
MAX_RETRIES   = 3
LOG_FILE      = "calorie_updates.log"
# ─────────────────────────────────────────────────────────────────────────

# ─── Secrets ─────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).with_suffix(".env"), override=False)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise SystemExit("🔐  OPENAI_API_KEY not found (set env var or .env file).")
client = OpenAI(api_key=api_key)
# ─────────────────────────────────────────────────────────────────────────

# ─── Logging ─────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("").addHandler(logging.StreamHandler(sys.stdout))
# ─────────────────────────────────────────────────────────────────────────

# ─── Firebase init ───────────────────────────────────────────────────────
cred = credentials.Certificate(SERVICE_KEY)
firebase_admin.initialize_app(cred)
db = firestore.client()
# ─────────────────────────────────────────────────────────────────────────


def already_processed(data: dict) -> bool:
    """
    Return True if the recipe was handled before.
    Criteria:
      • 'processed' flag is True
          OR
      • both 'calories' and 'cooking_time' fields exist
    """
    return (
        data.get("processed") is True
        or ("calories" in data and "cooking_time" in data)
    )


def ask_nutrition(name: str, directions: str) -> tuple[int | None, int | None]:
    """Return (calories, cooking_time_minutes) via OpenAI Chat."""
    sys_msg = (
        "You are an experienced nutritionist and chef. "
        "Respond ONLY in pure JSON (no markdown): "
        '{"calories": <int>, "cooking_time_minutes": <int>}.'
    )
    user_msg = f"Recipe name: {name}\nDirections:\n{directions}"

    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                temperature=TEMPERATURE,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user",   "content": user_msg},
                ],
            )
            data = json.loads(resp.choices[0].message.content)
            return int(data["calories"]), int(data["cooking_time_minutes"])
        except (RateLimitError, APIError):
            time.sleep(2 ** attempt)           # back-off & retry
        except (ValueError, KeyError, json.JSONDecodeError):
            pass                               # malformed JSON → retry
    return None, None


def main() -> None:
    docs = list(db.collection(COLLECTION).stream())     # snapshot

    for doc in tqdm(docs, desc="Processing"):
        data = doc.to_dict()
        if already_processed(data):
            continue                                    # skip

        name = data.get("title") or data.get("name")
        body = data.get("directions") or data.get("content")
        if not (name and body):
            logging.warning("Skipping %s (missing name/body)", doc.id)
            continue

        calories, cook_time = ask_nutrition(name, body)
        if calories is None or cook_time is None:
            logging.warning("OpenAI failed for %s", name)
            continue

        update = {
            "calories": calories,
            "cooking_time": cook_time,
            "processed": True,           # mark as done
        }
        doc.reference.update(update)
        logging.info("%s: %s kcal | %s min", name, calories, cook_time)


if __name__ == "__main__":
    main()

