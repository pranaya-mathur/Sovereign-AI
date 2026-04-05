import os
import argparse
import pandas as pd
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
from sklearn.model_selection import train_test_split
import logging
import torch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def fine_tune_model(dataset_path: str, model_name: str = "all-MiniLM-L6-v2", output_dir: str = "models/custom_embeddings", epochs: int = 4, batch_size: int = 16):
    """Fine-tune the sentence transformer on custom enterprise domain data using CosineSimilarityLoss.
    
    The dataset should be a CSV with two columns:
    - text: The input prompt/response.
    - label: Float score (1.0 for highly related to a failure class, 0.0 for unrelated).
    """
    logger.info(f"🚀 Starting Domain Fine-Tuning for {model_name}")
    
    if not os.path.exists(dataset_path):
        logger.error(f"❌ Dataset not found at {dataset_path}")
        return
        
    df = pd.read_csv(dataset_path)
    if 'text' not in df.columns or 'label' not in df.columns:
        logger.error("❌ Dataset must contain 'text' and 'label' columns")
        return

    # Determine Device
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    logger.info(f"💻 Utilizing Accelerator: {device}")

    # Load Base Model
    logger.info("Loading base embedding model...")
    model = SentenceTransformer(model_name, device=device)
    
    # Prepare Training Data
    logger.info("Preparing training data...")
    train_examples = []
    for _, row in df.iterrows():
        # Contrastive learning uses a single sentence and a label with CosineSimilarityLoss
        # Alternatively, we could use a pair of sentences. Assuming 'text' and a 'label' mapping.
        # Since we use CosineSimilarityLoss by default, it requires sentence pairs.
        # For simplicity in this enterprise pipeline, assuming the dataset provides 'text1', 'text2', 'label'.
        # If the user only passed 'text' and 'label', we adapt by pairing it against a known pattern.
        # For this script, we'll assume the user provides text1, text2, and label representing similarity.
        if 'text1' in df.columns and 'text2' in df.columns:
            train_examples.append(InputExample(texts=[row['text1'], row['text2']], label=float(row['label'])))
        else:
            logger.error("❌ Dataset must contain 'text1', 'text2' and 'label' columns for ContrastiveLoss")
            return
            
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)
    train_loss = losses.CosineSimilarityLoss(model=model)
    
    # OS agnostic pathing
    output_path = os.path.join(output_dir, model_name)
    os.makedirs(output_path, exist_ok=True)
    
    # Fine-Tune
    logger.info(f"🔥 Fine-tuning started for {epochs} epochs...")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=int(len(train_dataloader) * 0.1),
        output_path=output_path,
        show_progress_bar=True
    )
    
    logger.info(f"✅ Success! Custom model saved to {output_path}")
    logger.info("The Sovereign AI SemanticDetector will automatically load this fine-tuned model on next restart.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sovereign AI: Domain Fine-Tuning Pipeline")
    parser.add_argument("--dataset", type=str, required=True, help="Path to CSV dataset containing text1, text2, and label (float 0.0 to 1.0) columns")
    parser.add_argument("--model", type=str, default="all-MiniLM-L6-v2", help="Base model to fine-tune")
    parser.add_argument("--epochs", type=int, default=4, help="Number of epochs")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size")
    
    args = parser.parse_args()
    fine_tune_model(args.dataset, args.model, epochs=args.epochs, batch_size=args.batch_size)
