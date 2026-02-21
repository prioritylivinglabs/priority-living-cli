"""Priority Living CLI — Local model management (download, infer, serve)."""

import os
import sys
from pathlib import Path


MODELS_DIR = Path.home() / ".priority-living" / "models"


def handle_models(args):
    if not args.models_action:
        print("Usage: pl models <download|infer|serve> ...")
        return

    if args.models_action == "download":
        download_model(args.model_name)
    elif args.models_action == "infer":
        run_inference(args.model_name, args.prompt, args.max_tokens)
    elif args.models_action == "serve":
        serve_model(args.model_name, args.port)
    else:
        print(f"Unknown models action: {args.models_action}")


def download_model(model_name):
    print(f"📥 Downloading model: {model_name}")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from huggingface_hub import snapshot_download
        local_dir = MODELS_DIR / model_name.replace("/", "--")
        snapshot_download(
            repo_id=model_name,
            local_dir=str(local_dir),
            local_dir_use_symlinks=False,
        )
        print(f"✅ Model saved to: {local_dir}")
    except ImportError:
        print("❌ huggingface_hub is required. Install it:")
        print("   pip install huggingface_hub")
    except Exception as e:
        print(f"❌ Download failed: {e}")


def run_inference(model_name, prompt, max_tokens=256):
    print(f"🧠 Running inference with: {model_name}")
    print(f"   Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
        import torch

        local_dir = MODELS_DIR / model_name.replace("/", "--")
        model_path = str(local_dir) if local_dir.exists() else model_name

        device = "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else (
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        print(f"   Device: {device}")

        pipe = pipeline("text-generation", model=model_path, device=device, max_new_tokens=max_tokens)
        result = pipe(prompt)
        print("\n── Output ──────────────────────────────────")
        print(result[0]["generated_text"])
        print("─────────────────────────────────────────────")
    except ImportError:
        print("❌ transformers and torch are required. Install them:")
        print("   pip install transformers torch")
    except Exception as e:
        print(f"❌ Inference failed: {e}")


def serve_model(model_name, port=8000):
    print(f"🌐 Starting model API server for: {model_name} on port {port}")

    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
        import torch
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json

        local_dir = MODELS_DIR / model_name.replace("/", "--")
        model_path = str(local_dir) if local_dir.exists() else model_name

        device = "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else (
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        print(f"   Loading model on {device}...")
        pipe = pipeline("text-generation", model=model_path, device=device)
        print(f"✅ Model loaded. Server running on http://localhost:{port}")

        class ModelHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}
                prompt = body.get("prompt", "")
                max_tokens = body.get("max_tokens", 256)

                result = pipe(prompt, max_new_tokens=max_tokens)
                response = json.dumps({"text": result[0]["generated_text"]})

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(response.encode())

            def log_message(self, format, *args):
                print(f"  📨 {args[0]}")

        HTTPServer(("0.0.0.0", port), ModelHandler).serve_forever()

    except ImportError:
        print("❌ transformers and torch are required. Install them:")
        print("   pip install transformers torch")
    except Exception as e:
        print(f"❌ Server failed: {e}")
