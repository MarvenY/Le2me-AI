# Le2me – AI‑Powered Cooking App

Welcome to **Le2me**, an open‑source mobile application (Flutter) that helps users discover, customise, and cook recipes with the help of a fine‑tuned Large Language Model (LLM). This repository contains:

1. **Data & Utility scripts** for harvesting structured recipe data and attaching high‑quality images.
2. **Model‑training pipeline** that retrieves domain knowledge (RAG) and fine‑tunes the `flan‑t5‑base` model to power the in‑app chatbot.

---

## 📂 Repository structure

```text
.
├── data/                       # Raw & processed datasets
│   ├── recipes_raw.csv
│   └── rag_corpus/            # TXT / Markdown knowledge base for RAG
├── scripts/
│   ├── fetch_recipes.py       # Pulls recipes from Firestore & enriches with images
│   ├── google_image_search.py # Custom Google Programmable Search → image URL
│   ├── calories.py            # (optional) Nutrition estimation helper
│   └── train_llm.py           # End‑to‑end RAG + fine‑tune pipeline
├── models/
│   └── flan‑t5‑le2me/         # Saved checkpoints & tokenizer
├── notebook/                  # Exploratory notebooks
└── app/                       # Flutter source (separate repo submodule)
```

---

## 🔧 Prerequisites

| Domain                                           | Version / Notes                    |
| ------------------------------------------------ | ---------------------------------- |
| Python                                           |  ≥ 3.10                            |
|  Pipenv / Poetry                                 |  (recommended)                     |
|  PyTorch + CUDA                                  |  GPU strongly advised for training |
|  Hugging Face `transformers`, `datasets`, `peft` |  See `requirements.txt`            |
|  Google Programmable Search API key & CX         |  Needed for image enrichment       |
|  Firebase service account key                    |  Access Firestore exports          |

---

## 🗂️ Scripts

### 1. `fetch_recipes.py`

**Purpose:**

- Pull batched recipe documents from **Firestore** (collection `default recipe`).
- For each document, query Google Programmable Search for a matching dish photo.
- Persist a canonical schema:

```jsonc
{
  "title": "Halibut Supreme",
  "ingredients": ["halibut", "cheddar cheese", "mayonnaise", "butter"],
  "directions": ["Clean and rinse halibut…", "Bake at 375°F for 30 min…"],
  "image_url": "https://…jpg",
  "calories": 410
}
```

**CLI usage:**

```bash
python scripts/fetch_recipes.py     --batch-size 500     --out data/recipes_raw.csv
```

### 2. `train_llm.py`

**Highlights:**

1. **RAG corpus build** – chunks markdown docs from `data/rag_corpus/` and embeds with `sentence-transformers/all-MiniLM-L6-v2`.
2. **Retrieval pipeline** – FAISS index + BM25 fallback.
3. **Supervised fine‑tuning (SFT)** of `google/flan-t5-base` on the task‑specific recipe Q&A pairs prepared from `data/recipes_raw.csv`.
4. **LoRA adapters** to keep GPU memory ≤ 16 GB.
5. **Checkpoint push** to Hugging Face Hub *(optional)*.

```bash
python scripts/train_llm.py     --model flan-t5-base     --train-file data/sft/train.jsonl     --val-file   data/sft/val.jsonl     --output-dir models/flan-t5-le2me     --wandb-project le2me-llm
```

The resulting model is ≈ 220 MB and answers queries such as:

> *“I have chicken, rice, and broccoli. Give me a 20‑minute dinner idea.”*

---

## 🚀 Running locally

```bash
# 1. Install deps
pip install -r requirements.txt

# 2. Export env vars
export GOOGLE_API_KEY="…"
export GOOGLE_CX="…"
export FIREBASE_CRED="serviceAccount.json"

# 3. Fetch / enrich recipes
python scripts/fetch_recipes.py

# 4. Train or pull latest model
python scripts/train_llm.py   #   or   huggingface-cli download …
```

---

## 📱 Mobile integration

The **Flutter** client (folder `app/`) loads recipes via REST and calls the fine‑tuned model through an **OpenAI‑compatible FastAPI gateway** (`/api/chat`). The image URLs returned by the enrichment script are displayed using `CachedNetworkImage` to ensure smooth scrolling and offline support.

---

## 🤝 Contributing

Pull requests are welcome! Please open an issue first to discuss what you would like to change.

1. Fork the repo & create a feature branch.
2. Follow the [commit message convention](https://www.conventionalcommits.org/).
3. Run `pre‑commit run --all-files` before pushing.

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

## 🙏 Acknowledgements

- Google & Hugging Face for their generous open‑source tooling.
- All recipe creators whose content powers Le2me.
