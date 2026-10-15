"""
B13 Agent Training on Kaggle TPU

Kaggle notebook entrypoint for fine-tuning the B13 agent.
This script trains the model to correctly call security tools
using the smolagents tool schema format.

Usage on Kaggle:
    1. Install packages from requirements_kaggle.txt
    2. Add HF_TOKEN secret in Kaggle notebook settings
    3. Upload the SFT dataset
    4. Run this notebook

Training approach:
    The model learns to generate tool calls in the smolagents format:
    <code>\nresult = tool_name(param1=value1, param2=value2)\n</code>
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add project to path
PROJECT_ROOT = os.getenv("B13_PROJECT_ROOT", "/kaggle/working/b13-agent")
os.environ["PYTHONPATH"] = PROJECT_ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")
sys.path.insert(0, PROJECT_ROOT)

# Kaggle paths
KAGGLE_DATASET_PATH = "/kaggle/input/b13-cybersecurity-sft"
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_OUTPUT_DIR = "/kaggle/working/b13-model-checkpoint"
KAGGLE_RESULTS_DIR = "/kaggle/working/results"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def setup_environment():
    """Set up the Kaggle environment."""
    logger.info("Setting up B13 Kaggle environment...")

    os.makedirs("/kaggle/working", exist_ok=True)
    os.makedirs(KAGGLE_RESULTS_DIR, exist_ok=True)

    if not HF_TOKEN:
        logger.warning("HF_TOKEN not found in environment.")
        logger.warning("Please add HF_TOKEN in Kaggle notebook secrets.")

    if os.path.exists(KAGGLE_DATASET_PATH):
        logger.info(f"Dataset found at: {KAGGLE_DATASET_PATH}")
    else:
        logger.warning(f"Dataset not found at: {KAGGLE_DATASET_PATH}")
        logger.warning("Please upload your SFT dataset to Kaggle.")

    return True


def export_tool_schemas_for_training():
    """Export tool schemas for training dataset generation."""
    from b13_agent.agent import export_tool_schemas

    schemas = export_tool_schemas()

    # Save schemas
    output_path = os.path.join(KAGGLE_RESULTS_DIR, "tool_schemas.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schemas, f, indent=2)

    logger.info(f"Tool schemas exported to: {output_path}")
    logger.info(f"Total tools: {len(schemas)}")

    return schemas


def build_system_prompt_with_tools(tool_schemas: dict) -> str:
    """Build system prompt that includes tool descriptions.

    This is the prompt format smolagents CodeAgent uses.
    The model learns to generate tool calls in this format.
    """
    tool_descriptions = []
    for name, schema in tool_schemas.items():
        desc = f"- {name}: {schema['description']}"
        if schema["inputs"]:
            params = ", ".join(
                f"{param_name} ({param_info.get('type', 'any')})"
                for param_name, param_info in schema["inputs"].items()
            )
            desc += f"\n  Parameters: {params}"
        tool_descriptions.append(desc)

    system_prompt = f"""You are B13, an autonomous cybersecurity AI agent.

You have access to the following tools:

{chr(10).join(tool_descriptions)}

To use a tool, write Python code that calls the tool function.
Example:
```python
result = port_scan(target="192.168.1.100", ports="1-65535")
print(result)
```

Always use your available tools to complete tasks.
Report findings in a structured format.
"""

    return system_prompt


def prepare_training_dataset(tool_schemas: dict, dataset_path: str = None):
    """Prepare the training dataset for fine-tuning.

    The dataset should contain examples of the agent using tools.
    Format: system prompt + user task + assistant tool call response.
    """
    system_prompt = build_system_prompt_with_tools(tool_schemas)

    # If dataset exists, load it
    if dataset_path and os.path.exists(dataset_path):
        logger.info(f"Loading existing dataset from: {dataset_path}")
        # Dataset loading logic depends on format
        # For now, we export the system prompt for reference
        prompt_path = os.path.join(KAGGLE_RESULTS_DIR, "system_prompt.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(system_prompt)
        logger.info(f"System prompt saved to: {prompt_path}")

    return system_prompt


def run_fine_tuning(model_name: str = "Qwen/Qwen2.5-Coder-32B-Instruct"):
    """Run fine-tuning on Kaggle TPU."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
    from peft import LoraConfig, get_peft_model
    from trl import SFTTrainer, SFTConfig
    from datasets import load_dataset

    logger.info(f"Loading model: {model_name}")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
        token=HF_TOKEN,
    )
    tokenizer.pad_token = tokenizer.eos_token

    # Load model for TPU
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        token=HF_TOKEN,
    )

    # Configure LoRA
    lora_config = LoraConfig(
        r=64,
        lora_alpha=128,
        lora_dropout=0.03,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Training arguments for TPU
    training_args = TrainingArguments(
        output_dir=MODEL_OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=8,
        learning_rate=1e-4,
        warmup_ratio=0.05,
        max_seq_length=4096,
        logging_steps=10,
        save_steps=100,
        bf16=True,
        gradient_checkpointing=True,
        optim="adamw_torch",
        report_to="none",
        tpu_num_cores=8,
    )

    # SFT configuration
    sft_config = SFTConfig(
        output_dir=MODEL_OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=8,
        learning_rate=1e-4,
        max_seq_length=4096,
        dataset_text_field="messages",
        packing=False,
        gradient_checkpointing=True,
    )

    # Load dataset from Kaggle input
    dataset_files = []
    if os.path.exists(KAGGLE_DATASET_PATH):
        for f in os.listdir(KAGGLE_DATASET_PATH):
            if f.endswith(".parquet"):
                dataset_files.append(os.path.join(KAGGLE_DATASET_PATH, f))

    if dataset_files:
        logger.info(f"Loading datasets: {dataset_files}")
        dataset = load_dataset("parquet", data_files=dataset_files)
    else:
        logger.warning("No parquet files found in dataset path")
        logger.info("Please upload your SFT dataset to Kaggle")
        return

    # Initialize trainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset["train"] if "train" in dataset else list(dataset.values())[0],
        args=sft_config,
    )

    # Start training
    logger.info("Starting fine-tuning on TPU...")
    trainer.train()

    # Save model
    logger.info(f"Saving model to {MODEL_OUTPUT_DIR}...")
    trainer.save_model(MODEL_OUTPUT_DIR)
    tokenizer.save_pretrained(MODEL_OUTPUT_DIR)

    logger.info("Training completed!")


def main():
    """Main entry point for Kaggle execution."""
    logger.info("=" * 60)
    logger.info("B13 Agent Training on Kaggle TPU")
    logger.info("=" * 60)

    # Setup
    setup_environment()

    # Export tool schemas
    schemas = export_tool_schemas_for_training()

    # Prepare training dataset
    system_prompt = prepare_training_dataset(schemas, KAGGLE_DATASET_PATH)

    # Run fine-tuning
    run_fine_tuning()

    logger.info("=" * 60)
    logger.info("B13 Kaggle training complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
