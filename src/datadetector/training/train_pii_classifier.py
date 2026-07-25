"""
Fine-tune Transformer models for PII detection.

Trains two models from the labeled dataset:
1. Binary classifier: PII vs Non-PII (used in _ml_context_check)
2. Category classifier: Multi-class PII type prediction (21 categories)

Usage:
    python -m datadetector.training.train_pii_classifier \
        --data-dir /path/to/dataset/ml/data \
        --output-dir /path/to/output \
        --base-model distilbert-base-uncased \
        --epochs 5 \
        --batch-size 16

Requires: pip install data-detector[transformer]
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PIIDataset(Dataset):
    """PyTorch dataset for PII text classification."""

    def __init__(
        self,
        texts: List[str],
        labels: List[int],
        tokenizer: AutoTokenizer,
        max_length: int = 128,
    ):
        self.encodings = tokenizer(
            texts,
            truncation=True,
            padding="max_length",
            max_length=max_length,
            return_tensors="pt",
        )
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        item = {key: val[idx] for key, val in self.encodings.items()}
        item["labels"] = self.labels[idx]
        return item


def load_data(data_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load train/val/test splits from parquet or CSV."""
    data_path = Path(data_dir)

    def load_split(name: str) -> pd.DataFrame:
        parquet = data_path / f"{name}.parquet"
        csv = data_path / f"{name}.csv"
        if parquet.exists():
            return pd.read_parquet(parquet)
        elif csv.exists():
            return pd.read_csv(csv)
        else:
            raise FileNotFoundError(f"No {name}.parquet or {name}.csv in {data_dir}")

    train_df = load_split("train")
    val_df = load_split("val")
    test_df = load_split("test")

    logger.info(
        f"Loaded data: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}"
    )
    return train_df, val_df, test_df


def build_category_mapping(df: pd.DataFrame) -> Tuple[Dict[str, int], Dict[int, str]]:
    """Build category->id and id->category mappings, excluding 'none'."""
    categories = sorted([c for c in df["category"].unique() if c != "none"])
    cat2id = {cat: i for i, cat in enumerate(categories)}
    id2cat = {i: cat for cat, i in cat2id.items()}
    logger.info(f"Category mapping: {len(cat2id)} classes: {categories}")
    return cat2id, id2cat


def compute_metrics(eval_pred: Tuple) -> Dict[str, float]:
    """Compute accuracy, precision, recall, F1 for evaluation."""
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    accuracy = (predictions == labels).mean()

    # Per-class metrics for multi-class, or binary metrics
    num_classes = logits.shape[1]
    if num_classes == 2:
        # Binary: positive class = 1
        tp = ((predictions == 1) & (labels == 1)).sum()
        fp = ((predictions == 1) & (labels == 0)).sum()
        fn = ((predictions == 0) & (labels == 1)).sum()
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
        }
    else:
        # Multi-class: macro F1
        from sklearn.metrics import f1_score, precision_score, recall_score

        return {
            "accuracy": float(accuracy),
            "precision_macro": float(precision_score(labels, predictions, average="macro", zero_division=0)),
            "recall_macro": float(recall_score(labels, predictions, average="macro", zero_division=0)),
            "f1_macro": float(f1_score(labels, predictions, average="macro", zero_division=0)),
            "f1_weighted": float(f1_score(labels, predictions, average="weighted", zero_division=0)),
        }


def train_binary_classifier(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    base_model: str,
    output_dir: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    max_length: int,
) -> Dict[str, float]:
    """Fine-tune a binary PII/Non-PII classifier."""
    logger.info("=" * 60)
    logger.info("Training Binary PII Classifier")
    logger.info("=" * 60)

    output_path = Path(output_dir) / "binary_classifier"
    output_path.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=2,
        id2label={0: "non_pii", 1: "pii"},
        label2id={"non_pii": 0, "pii": 1},
    )

    train_dataset = PIIDataset(
        train_df["text"].tolist(), train_df["label"].tolist(), tokenizer, max_length
    )
    val_dataset = PIIDataset(
        val_df["text"].tolist(), val_df["label"].tolist(), tokenizer, max_length
    )
    test_dataset = PIIDataset(
        test_df["text"].tolist(), test_df["label"].tolist(), tokenizer, max_length
    )

    # Class weights for imbalanced data
    n_pos = (train_df["label"] == 1).sum()
    n_neg = (train_df["label"] == 0).sum()
    weight_pos = len(train_df) / (2.0 * n_pos)
    weight_neg = len(train_df) / (2.0 * n_neg)
    class_weights = torch.tensor([weight_neg, weight_pos], dtype=torch.float32)
    logger.info(f"Class weights: non_pii={weight_neg:.3f}, pii={weight_pos:.3f}")

    training_args = TrainingArguments(
        output_dir=str(output_path / "checkpoints"),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size * 2,
        learning_rate=learning_rate,
        weight_decay=0.01,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        logging_steps=50,
        report_to="none",
        seed=42,
    )

    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            logits = outputs.logits
            loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights.to(logits.device))
            loss = loss_fn(logits, labels)
            return (loss, outputs) if return_outputs else loss

    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    logger.info("Starting binary classifier training...")
    trainer.train()

    # Evaluate on test set
    logger.info("Evaluating on test set...")
    test_metrics = trainer.evaluate(test_dataset, metric_key_prefix="test")
    logger.info(f"Test metrics: {test_metrics}")

    # Save final model + tokenizer
    final_path = str(output_path / "final")
    model.save_pretrained(final_path)
    tokenizer.save_pretrained(final_path)
    logger.info(f"Binary classifier saved to {final_path}")

    return test_metrics


def train_category_classifier(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    base_model: str,
    output_dir: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    max_length: int,
) -> Dict[str, float]:
    """Fine-tune a multi-class PII category classifier."""
    logger.info("=" * 60)
    logger.info("Training Category Classifier")
    logger.info("=" * 60)

    output_path = Path(output_dir) / "category_classifier"
    output_path.mkdir(parents=True, exist_ok=True)

    # Filter to PII-only samples for category classification
    train_pii = train_df[train_df["label"] == 1].copy()
    val_pii = val_df[val_df["label"] == 1].copy()
    test_pii = test_df[test_df["label"] == 1].copy()
    logger.info(
        f"PII samples: train={len(train_pii)}, val={len(val_pii)}, test={len(test_pii)}"
    )

    # Build category mapping
    cat2id, id2cat = build_category_mapping(train_pii)
    num_labels = len(cat2id)

    # Map categories to IDs
    train_labels = [cat2id[c] for c in train_pii["category"]]
    val_labels = [cat2id.get(c, 0) for c in val_pii["category"]]
    test_labels = [cat2id.get(c, 0) for c in test_pii["category"]]

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=num_labels,
        id2label=id2cat,
        label2id=cat2id,
    )

    train_dataset = PIIDataset(
        train_pii["text"].tolist(), train_labels, tokenizer, max_length
    )
    val_dataset = PIIDataset(
        val_pii["text"].tolist(), val_labels, tokenizer, max_length
    )
    test_dataset = PIIDataset(
        test_pii["text"].tolist(), test_labels, tokenizer, max_length
    )

    training_args = TrainingArguments(
        output_dir=str(output_path / "checkpoints"),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size * 2,
        learning_rate=learning_rate,
        weight_decay=0.01,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,
        logging_steps=50,
        report_to="none",
        seed=42,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    logger.info("Starting category classifier training...")
    trainer.train()

    # Evaluate on test set
    logger.info("Evaluating on test set...")
    test_metrics = trainer.evaluate(test_dataset, metric_key_prefix="test")
    logger.info(f"Test metrics: {test_metrics}")

    # Save final model + tokenizer + category mapping
    final_path = str(output_path / "final")
    model.save_pretrained(final_path)
    tokenizer.save_pretrained(final_path)

    mapping_path = os.path.join(final_path, "category_mapping.json")
    with open(mapping_path, "w") as f:
        json.dump({"cat2id": cat2id, "id2cat": {str(k): v for k, v in id2cat.items()}}, f, indent=2)

    logger.info(f"Category classifier saved to {final_path}")
    return test_metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fine-tune Transformer models for PII detection"
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing train/val/test parquet or CSV files",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save fine-tuned models",
    )
    parser.add_argument(
        "--base-model",
        default="distilbert-base-uncased",
        help="HuggingFace base model name (default: distilbert-base-uncased)",
    )
    parser.add_argument(
        "--epochs", type=int, default=5, help="Number of training epochs (default: 5)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Training batch size (default: 16)",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-5,
        help="Learning rate (default: 2e-5)",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=128,
        help="Max token sequence length (default: 128)",
    )
    parser.add_argument(
        "--binary-only",
        action="store_true",
        help="Train only the binary classifier",
    )
    parser.add_argument(
        "--category-only",
        action="store_true",
        help="Train only the category classifier",
    )
    args = parser.parse_args()

    train_df, val_df, test_df = load_data(args.data_dir)

    all_metrics = {}

    if not args.category_only:
        binary_metrics = train_binary_classifier(
            train_df, val_df, test_df,
            args.base_model, args.output_dir, args.epochs,
            args.batch_size, args.learning_rate, args.max_length,
        )
        all_metrics["binary"] = binary_metrics

    if not args.binary_only:
        category_metrics = train_category_classifier(
            train_df, val_df, test_df,
            args.base_model, args.output_dir, args.epochs,
            args.batch_size, args.learning_rate, args.max_length,
        )
        all_metrics["category"] = category_metrics

    # Save combined metrics
    metrics_path = os.path.join(args.output_dir, "training_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(all_metrics, f, indent=2)
    logger.info(f"All metrics saved to {metrics_path}")

    # Summary
    logger.info("=" * 60)
    logger.info("Training Complete!")
    logger.info("=" * 60)
    for task, metrics in all_metrics.items():
        logger.info(f"\n{task}:")
        for k, v in metrics.items():
            if isinstance(v, float):
                logger.info(f"  {k}: {v:.4f}")


if __name__ == "__main__":
    main()
