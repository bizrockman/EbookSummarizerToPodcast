import os

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq


def get_chat_llm(model_name=None, temperature=0, max_tokens=None, base_url=None, llm_model_provider=None) -> BaseChatModel:
    if not llm_model_provider:
        llm_model_provider = get_llm_model_provider()

    if not base_url:
        if llm_model_provider == "groq":
            base_url = os.getenv("GROQ_API_BASE")

    if not model_name:
        if llm_model_provider == "groq":
            model_name = os.getenv("GROQ_DEFAULT_MODEL")
        elif llm_model_provider == "openai":
            model_name = os.getenv("OPENAI_DEFAULT_MODEL")

    if llm_model_provider == "openai":
        return ChatOpenAI(model_name=model_name, temperature=temperature, max_tokens=max_tokens, base_url=base_url)
    elif llm_model_provider == "groq":
        return ChatGroq(model_name=model_name, temperature=temperature, max_tokens=max_tokens, groq_api_base=base_url, max_retries=3)


def get_llm_model_provider() -> str:
    llm_model_provider = os.getenv("LLM_MODEL_PROVIDER")

    if not llm_model_provider:
        llm_model_provider = "openai"

    return llm_model_provider
