from transformers import AutoTokenizer, AutoModelForSequenceClassification
from accelerate import infer_auto_device_map, dispatch_model
from torch.nn.functional import softmax
import torch
import os

def analyze_sentiment(text):
    """
    Analyze emotions in the provided text.
    
    Args:
        text (str): The text to analyze for emotions
        
    Returns:
        list: List of tuples containing (emotion, score) sorted by score
    """
    # Initialize model (Note: This is inefficient if the function is called multiple times)
    # Define model path

    model_dir = "models/emotion_model"

    # Load from local directory
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir, from_tf=True)

    # Configure device mapping
    device_map = infer_auto_device_map(model, no_split_module_classes=["BertLayer"], dtype=torch.float16)
    model = dispatch_model(model, device_map=device_map)
    
    # Tokenize
    inputs = tokenizer(text, return_tensors="pt", truncation=True).to(model.device)
    
    # Inference
    with torch.no_grad():
        logits = model(**inputs).logits
        probs = softmax(logits, dim=1)
    
    # Interpret results
    labels = model.config.id2label
    probs_dict = {labels[i]: float(probs[0][i]) for i in range(len(labels))}
    sorted_emotions = sorted(probs_dict.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_emotions


# Example usage when run directly
if __name__ == "__main__":
    frase = "Estou muito emocionado com a notícia que recebi hoje."
    emotions = analyze_sentiment(frase)
    
    print("\n🔍 Emoções detectadas:")
    for emotion, score in emotions[:5]:
        print(f"{emotion}: {score:.4f}")
