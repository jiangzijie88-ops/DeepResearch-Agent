"""Environment-configured LangChain chat model factory."""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()


def get_model() -> ChatOpenAI:
    """Build the shared LangChain chat model (DeepSeek by default).

    Read LLM_PROVIDER and the selected provider's API_KEY, MODEL and BASE_URL
    environment variables, e.g. DEEPSEEK_BASE_URL. All three are required.
    Supports bind_tools() and Pydantic with_structured_output(); for DeepSeek,
    use method="function_calling" rather than OpenAI-native JSON Schema output.
    """
    provider = os.getenv("LLM_PROVIDER", "deepseek").strip().lower()
    if provider not in {"deepseek", "openai"}:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

    prefix = provider.upper()
    names = [f"{prefix}_{suffix}" for suffix in ("API_KEY", "MODEL", "BASE_URL")]
    values = [os.getenv(name, "").strip() for name in names]
    missing = [name for name, value in zip(names, values) if not value]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    api_key, model_name, base_url = values
    return ChatOpenAI(
        api_key=api_key,
        model=model_name,
        base_url=base_url,
        temperature=0,
        use_responses_api=False,
        # Structured schemas and the first search turn require forced tools.
        extra_body={"thinking": {"type": "disabled"}} if provider == "deepseek" else None,
    )
