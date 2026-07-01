import os
import sys

from pipeline.settings import get_settings
from pipeline.llm.factory import get_client


def main() -> None:
    settings = get_settings()

    provider = os.getenv("LLM_PROVIDER", "ollama")
    model = os.getenv("LLM_MODEL", settings.ollama_models[0] if settings.ollama_models else "llama3")

    provider_model = f"{provider}:{model}"
    print(f"Instantiating client for: {provider_model}")

    try:
        client = get_client(provider_model, settings)
    except Exception as e:
        print(f"Error instantiating client: {e}")
        sys.exit(1)

    # TODO(Phase 3): replace with real pipeline prompt loaded from pipeline/prompts/
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
