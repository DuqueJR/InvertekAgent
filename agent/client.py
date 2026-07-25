from anthropic import Anthropic

from .config import DEEPSEEK_API_KEY, ANTHROPIC_BASE_URL


def create_client():
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY no está configurada.")

    return Anthropic(
        api_key=DEEPSEEK_API_KEY,
        base_url=ANTHROPIC_BASE_URL,
    )