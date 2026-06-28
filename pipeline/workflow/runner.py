from __future__ import annotations

import sys

from pipeline.settings import get_settings
from pipeline.llm.factory import get_client


def main() -> None:
    """Main entry point for the pipeline runner."""
    print("Loading settings...")
    settings = get_settings()
    
    #  We use "ollama:llama3" as default or read from env.
    provider_model = "ollama:llama3"
    print(f"Instantiating client for: {provider_model}")
    try:
        client = get_client(provider_model, settings)
    except Exception as e:
        print(f"Error instantiating client: {e}")
        sys.exit(1)
        
    prompt = "Quanto é 1 + 1?"
    print(f"Sending prompt to LLM: '{prompt}'")
    try:
        response = client.complete(prompt, max_tokens=100)
        print("\n=== LLM Response ===")
        print(response.text)
        print("====================\n")
        print(f"Model used: {response.model}")
        print(f"Provider: {response.provider}")
        print(f"Latency: {response.latency_seconds:.2f}s")
    except Exception as e:
        print(f"Error completing request: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
