import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel, set_tracing_disabled


# 读取 .env 文件,
load_dotenv()


# 暂时关闭 OpenAI Agents SDK 的 tracing
set_tracing_disabled(True)


def get_model():

    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    # =========================
    # OpenAI
    # =========================
    if provider == "openai":

        api_key = os.getenv("OPENAI_API_KEY")
        model_name = os.getenv("OPENAI_MODEL")

        if not api_key:
            raise ValueError(
                "没有找到 OPENAI_API_KEY，请检查 .env 文件。"
            )

        client = AsyncOpenAI(
            api_key=api_key
        )

        model = OpenAIChatCompletionsModel(
            model=model_name,
            openai_client=client
        )

        return model

    # =========================
    # DeepSeek
    # =========================
    elif provider == "deepseek":

        api_key = os.getenv("DEEPSEEK_API_KEY")
        model_name = os.getenv("DEEPSEEK_MODEL")

        if not api_key:
            raise ValueError(
                "没有找到 DEEPSEEK_API_KEY，请检查 .env 文件。"
            )

        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        model = OpenAIChatCompletionsModel(
            model=model_name,
            openai_client=client
        )

        return model

    # =========================
    # 不支持的供应商
    # =========================
    else:
        raise ValueError(
            f"暂不支持模型供应商：{provider}"
        )