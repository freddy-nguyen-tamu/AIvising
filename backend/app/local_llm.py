from functools import lru_cache

from app.config import settings


@lru_cache(maxsize=1)
def load_local_adapter():
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "Local adapter inference requires transformers, peft, and torch. "
            "Install the optional training requirements first."
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(settings.local_base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base_model = AutoModelForCausalLM.from_pretrained(
        settings.local_base_model,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    model = PeftModel.from_pretrained(base_model, settings.local_adapter_path)
    return tokenizer, model


def render_prompt(messages: list[dict]) -> str:
    return "\n\n".join(f"{message['role'].upper()}:\n{message['content']}" for message in messages)


def generate_local_adapter_answer(messages: list[dict]) -> str:
    tokenizer, model = load_local_adapter()
    prompt = render_prompt(messages)

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
    if hasattr(model, "device"):
        inputs = {key: value.to(model.device) for key, value in inputs.items()}

    outputs = model.generate(
        **inputs,
        max_new_tokens=settings.local_max_new_tokens,
        temperature=settings.llm_temperature,
        do_sample=settings.llm_temperature > 0,
        pad_token_id=tokenizer.eos_token_id,
    )

    generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return generated[len(prompt):].strip() if generated.startswith(prompt) else generated.strip()
