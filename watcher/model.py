"""Model selection for the watcher agent.

One knob, `MODEL_PROVIDER`, so the same agent runs on Bedrock (the AWS-native
path), on the Anthropic API, or fully offline on Ollama. The provider is
DECLARED, never guessed: an unset variable picks Bedrock and says so, because
silently falling back to a different provider would change what the demo proves.
"""

from __future__ import annotations

import os


class ModelUnavailable(RuntimeError):
    """Raised when the chosen provider cannot be built, with the reason."""


def build_model():
    """Return a Strands model object plus a one-line human description of it."""
    provider = os.environ.get("MODEL_PROVIDER", "bedrock").strip().lower()

    if provider == "bedrock":
        from strands.models import BedrockModel

        model_id = os.environ.get(
            "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        )
        region = os.environ.get("AWS_REGION", "us-east-1")
        return BedrockModel(model_id=model_id, region_name=region), (
            f"Amazon Bedrock · {model_id} · {region}"
        )

    if provider == "anthropic":
        from strands.models.anthropic import AnthropicModel

        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ModelUnavailable(
                "MODEL_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set."
            )
        model_id = os.environ.get("ANTHROPIC_MODEL_ID", "claude-sonnet-4-5-20250929")
        return AnthropicModel(client_args={"api_key": key}, model_id=model_id), (
            f"Anthropic API · {model_id}"
        )

    if provider == "mnemosyne":
        # Mnemosyne's own loopback brain proxy: an OpenAI-compatible endpoint
        # serving the inference the human already pays for, metered and capped
        # by the host. The agent's brain and its memory then come from the same
        # machine, and no provider key is ever copied into this repository.
        from strands.models.openai import OpenAIModel

        key = os.environ.get("MNEMO_PROXY_KEY")
        if not key:
            raise ModelUnavailable(
                "MODEL_PROVIDER=mnemosyne but MNEMO_PROXY_KEY is not set. "
                "Mnemosyne OS > Settings > Hermes shows the brain-proxy block."
            )
        base_url = os.environ.get("MNEMO_PROXY_URL", "http://127.0.0.1:7439/v1")
        model_id = os.environ.get("MNEMO_PROXY_MODEL", "mnemosyne")
        return OpenAIModel(
            client_args={"api_key": key, "base_url": base_url}, model_id=model_id
        ), f"Mnemosyne brain proxy · {model_id} · {base_url}"

    if provider == "ollama":
        from strands.models.ollama import OllamaModel

        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        model_id = os.environ.get("OLLAMA_MODEL_ID", "qwen3:8b")
        return OllamaModel(host=host, model_id=model_id), (
            f"Ollama (local) · {model_id} · {host}"
        )

    raise ModelUnavailable(
        f"Unknown MODEL_PROVIDER {provider!r}. "
        "Use bedrock, anthropic, mnemosyne or ollama."
    )
