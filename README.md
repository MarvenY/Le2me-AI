# Overwrite README.md with updated content from canvas
updated_readme = """# Le2me-AI – Recipe Data Pipelines & LLM Training

> **One repo – two jobs:**
> 1. **Data enrichment** → pull recipes from Firestore, attach high-quality images, and compute nutrition facts.
> 2. **Model training** → build a retrieval-augmented dataset and fine-tune `flan-t5-base` to power the Le2me in-app chatbot.

---

## 📁 File overview

| File / Dir                     | Purpose |
| ------------------------------ | ------- |
| `image_fetch.py`               | Fetches recipe docs from Firestore and uses **Google Programmable Search** to attach an `image_url` to each record. |
| `calories_populating.py`       | Estimates calories & macro-nutrients for every recipe (OpenAI function calls) and appends results to Firestore. |
| `calorie_updates.log`          | Rolling logfile produced by the nutrition script. |
| `calories.env`                 | API keys & environment variables required by the calorie script (**NOT** committed – add your own). |
| `fine_tune_flan_recipes.py`    | Preps SFT / RAG training data: builds FAISS index, generates instruction–response pairs. |
| `AI_Train.py`                  | **Entrypoint** – orchestrates RAG + LoRA fine-tuning of `google/flan-t5-base`, saves checkpoints under `models/`. |
| `README.md`                    | You are here. |

