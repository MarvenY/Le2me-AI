# train.py ─ Fine-tune FLAN-T5-Base (fully “unlocked”) on a recipe dataset
import os
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"   # safe to leave even on Windows

from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)
import torch

# ──────────────────────────────────────────────────────────────────────────────
# 1. Load dataset
raw_ds   = load_dataset("Shengtao/recipe")     # ingredients ➜ directions
train_ds = raw_ds["train"]

# ──────────────────────────────────────────────────────────────────────────────
# 2. Load tokenizer & model
model_name = "google/flan-t5-base"
tokenizer  = AutoTokenizer.from_pretrained(model_name)
model      = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# Disable dropout so nothing is “held back”
for attr in [
    "dropout_rate",
    "attention_dropout_rate",
    "classifier_dropout",
]:
    if hasattr(model.config, attr):
        setattr(model.config, attr, 0.0)

# ──────────────────────────────────────────────────────────────────────────────
# 3. Pre-processing
def preprocess(example):
    return tokenizer(
        example["ingredients"],
        text_target=example["directions"],
        truncation=True,
    )

encoded_ds = train_ds.map(preprocess, batched=True)

# ──────────────────────────────────────────────────────────────────────────────
# 4. Training arguments  (no processing_class line)
training_args = Seq2SeqTrainingArguments(
    output_dir=r"C:\flan-t5",
    overwrite_output_dir=True,
    num_train_epochs=3,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=16,      # effective batch size = 16
    learning_rate=5e-5,
    warmup_steps=250,
    logging_dir=r"C:\logs",
    logging_steps=50,
    save_strategy="epoch",
    save_total_limit=1,
    fp16=torch.cuda.is_available(),
    bf16=not torch.cuda.is_available(),  # BF16 if CPU + PyTorch ≥ 2.2
    report_to="none",
)

data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

# ──────────────────────────────────────────────────────────────────────────────
# 5. Trainer
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=encoded_ds,
    tokenizer=tokenizer,
    data_collator=data_collator,
)

if __name__ == "__main__":
    trainer.train()

    # ──────────────────────────────────────────────────────────────────────────
    # 6. Save fine-tuned model
    out_dir = r"C:\flan-t5-custom"
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    print("\n✅ Training complete — model saved to:", out_dir)
