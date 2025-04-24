#  Fine-Tune FLAN-T5-Small on Recipe Dataset (Ingredients ➜ Directions)
import os
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"

from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, Seq2SeqTrainer, Seq2SeqTrainingArguments, DataCollatorForSeq2Seq
import torch

# 1. Load Dataset from Hugging Face
raw_dataset = load_dataset("Shengtao/recipe")
dataset = raw_dataset["train"]

# 2. Load Tokenizer and Model
model_name = "google/flan-t5-small"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# 3. Preprocess: Format to input/output pair
def preprocess_function(example):
    input_text = example["ingredients"]
    target_text = example["directions"]
    return tokenizer(input_text, text_target=target_text, truncation=True)

# Apply preprocessing
encoded_dataset = dataset.map(preprocess_function, batched=True)

# 4. Set up training arguments
training_args = Seq2SeqTrainingArguments(
    output_dir="./flan-t5-recipes",
    per_device_train_batch_size=1,
    learning_rate=5e-5,
    num_train_epochs=3,
    save_total_limit=1,
    save_strategy="epoch",
    logging_dir="./logs",
    fp16=torch.cuda.is_available(),
    max_steps=50,
)

# 5. Data collator handles dynamic padding
data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

# 6. Create Trainer
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=encoded_dataset,
    tokenizer=tokenizer,
    data_collator=data_collator,
)

# 7. Train the model
trainer.train()

# 8. Save your custom model
model.save_pretrained("./flan-t5-recipes-custom")
tokenizer.save_pretrained("./flan-t5-recipes-custom")

print("\n Training complete. Your fine-tuned recipe model is saved!")
