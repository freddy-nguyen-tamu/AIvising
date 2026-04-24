from pathlib import Path

from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments


BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
DATA_FILE = Path("training/advising_finetune.jsonl")
OUTPUT_DIR = Path("training/output/advising-lora")
MAX_LENGTH = 1024


def format_example(example, tokenizer):
    text = ""
    for message in example["messages"]:
        text += f"<|{message['role']}|>\n{message['content']}\n"
    text += "<|end|>"

    tokens = tokenizer(
        text,
        truncation=True,
        padding="max_length",
        max_length=MAX_LENGTH,
    )
    tokens["labels"] = tokens["input_ids"].copy()
    return tokens


def main():
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dataset = load_dataset("json", data_files=str(DATA_FILE))["train"]
    tokenized = dataset.map(
        lambda row: format_example(row, tokenizer),
        remove_columns=dataset.column_names,
    )

    base_model = AutoModelForCausalLM.from_pretrained(BASE_MODEL)
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(base_model, lora_config)

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        num_train_epochs=2,
        logging_steps=10,
        save_steps=50,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
    )

    trainer.train()
    model.save_pretrained(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))


if __name__ == "__main__":
    main()
