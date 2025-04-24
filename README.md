# Le2me‑AI – Recipe Data Pipelines & LLM Training

> **One repo – two jobs:**  
> 1. **Data enrichment** → pull recipes from Firestore, attach high‑quality images, and compute nutrition facts.  
> 2. **Model training** → build a retrieval‑augmented dataset and fine‑tune **`flan‑t5‑base`** to power the Le2me in‑app chatbot.

---

## 📁 File overview

| Path / File                    | Purpose |
| ------------------------------ | ------- |
| `image_fetch.py`               | Fetches recipe docs from Firestore & adds `image_url` via **Google Programmable Search** |
| `calories_populating.py`       | Calls OpenAI to estimate calories/macros and patches Firestore; logs to `calorie_updates.log` |
| `calorie_updates.log`          | Rolling logfile from the nutrition script |
| `calories.env` †               | API keys & env vars (**keep secret**) |
| `fine_tune_flan_recipes.py`    | Builds FAISS index & generates instruction‑response pairs for SFT |
| `AI_Train.py`                  | **Entrypoint** – orchestrates RAG + LoRA fine‑tuning of `flan‑t5‑base` |
| `models/` *generated*          | Checkpoints & tokenizer |
| `README.md`                    | You’re reading it |

```text
LE2ME‑AI/
├── AI_Train.py
├── calorie_updates.log
├── calories_populating.py
├── calories.env            # ← not committed
├── fine_tune_flan_recipes.py
├── image_fetch.py
├── models/                 # saved adapters
└── README.md
```

† Copy `calories.env.example` ➜ `calories.env` and add your own keys.

---

## 🔧 Quick start

```bash
# 1️⃣  Install deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2️⃣  Export secrets
cp calories.env.example calories.env
export $(grep -v '^#' calories.env | xargs)

# 3️⃣  Enrich recipes with images
python image_fetch.py \
  --collection "default recipe" --page-size 250 \
  --out data/recipes_with_images.jsonl

# 4️⃣  Populate calories
python calories_populating.py --input data/recipes_with_images.jsonl

# 5️⃣  Fine‑tune LLM
python AI_Train.py \
  --base-model flan-t5-base \
  --recipes data/recipes_with_images.jsonl \
  --output models/flan-t5-le2me
```

---

## ⚙️ Workflow details

### Image enrichment (`image_fetch.py`)
*Queries Google once per recipe (≤100 QPM).*  
Adds `image_url` and writes merged JSONL.

### Nutrition (`calories_populating.py`)
* Uses OpenAI function calls for per‑ingredient nutrition.  
* Appends fields `calories`, `protein`, `fat`, `carbs`; writes progress to `calorie_updates.log`.

### Model training (`AI_Train.py`)
1. **RAG corpus** from recipe steps + external docs.  
2. **SFT dataset** via `fine_tune_flan_recipes.py`.  
3. **LoRA** fine‑tuning of `flan‑t5‑base` (≈3 h on one A100).  
4. Saves adapters to `models/flan-t5-le2me` — 220 MB.

---

## 📱 Mobile integration

The Flutter app (separate repo) hits:
* `/api/recipes` – list enriched recipes with `image_url`  
* `/api/chat` – OpenAI‑style endpoint backed by the fine‑tuned model

Images are loaded with `CachedNetworkImage` for smooth scrolling & caching.

---

## 🤝 Contributing

1. Fork, create a feature branch.  
2. Follow [Conventional Commits](https://www.conventionalcommits.org/).  
3. Run `pre‑commit run --all-files` before pushing.

---

## 📜 License

MIT

---

### 🙏 Acknowledgements

* Google Programmable Search & Firebase  
* Hugging Face (Transformers, PEFT)  
* All original recipe creators whose content powers Le2me
