"""
Disaster-Whisper: Small Language Model (SLM) Setup Utility
=========================================================
This script downloads and caches the supported Small Language Models (SLMs)
for real on-device alert generation (Tier 2 pathway).

It checks for the required libraries and downloads the selected model
into the local cache directory: `model/slm_cache`.

Recommended Model: Qwen/Qwen1.5-1.8B-Chat (~1.5 GB download)
  - Excellent multilingual support (English & Hindi)
  - Fit for consumer hardware (4GB+ RAM)
"""

import os
import sys

# Ensure project modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.tier2_engine import SUPPORTED_MODELS, _MODEL_CACHE_DIR


def download_model(model_id: str):
    print(f"\nPreparing to download model: '{model_id}'")
    print(f"Destination: {os.path.abspath(_MODEL_CACHE_DIR)}")
    
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
    except ImportError:
        print("\n[ERROR] Required packages 'transformers' or 'torch' are not installed.")
        print("Please run: pip install transformers torch")
        return False

    # Create target directory for this specific model
    # replace '/' with '--' to match huggingface cache conventions
    safe_folder = model_id.replace("/", "--")
    target_dir = os.path.join(_MODEL_CACHE_DIR, safe_folder)
    os.makedirs(target_dir, exist_ok=True)

    print(f"\nStarting download via HuggingFace hub snapshot... (This may take several minutes)")
    print("Files will be saved directly to the local project model folder.")

    try:
        from huggingface_hub import snapshot_download
        
        snapshot_download(
            repo_id=model_id,
            local_dir=target_dir,
            local_dir_use_symlinks=False,
            ignore_patterns=["*.msgpack", "*.h5", "*.ot"], # save space, ignore other weights formats
        )
        
        print(f"\n{'-'*60}")
        print(f"SUCCESS: Model '{model_id}' successfully downloaded and cached.")
        print(f"Directory: {os.path.abspath(target_dir)}")
        print(f"{'-'*60}")
        
        # Quick validation
        print("\nVerifying files...")
        tokenizer = AutoTokenizer.from_pretrained(target_dir)
        print("✓ Tokenizer load verified.")
        print("\nAll systems ready for Tier 2 on-device SLM synthesis.")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Failed to download model: {e}")
        print("Please ensure you have an active internet connection and write permissions.")
        return False


def main():
    print("=" * 70)
    print("      DISASTER-WHISPER: SLM DOWNLOAD & SETUP UTILITY")
    print("=" * 70)
    
    print("\nSupported on-device models:")
    for idx, model in enumerate(SUPPORTED_MODELS):
        rec_label = " (RECOMMENDED)" if model["recommended"] else ""
        print(f"  [{idx + 1}] {model['nickname']} ({model['model_id']})")
        print(f"      Size: ~{model['size_gb']} GB{rec_label}")
    
    print("\n[Note] Qwen-1.8B-Chat is highly recommended due to Hindi support.")
    
    # In interactive environments, let the user select.
    # In non-interactive or scripts, we can accept arguments or default to 1 (Qwen).
    choice = "1"
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(SUPPORTED_MODELS):
            selected = SUPPORTED_MODELS[idx]
        else:
            print("Invalid choice, defaulting to Qwen.")
            selected = SUPPORTED_MODELS[0]
    except ValueError:
        selected = SUPPORTED_MODELS[0]

    print(f"\nSelected Model: {selected['nickname']}")
    
    success = download_model(selected["model_id"])
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
