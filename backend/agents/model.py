"""The one model every Wishing Tree agent uses.

gpt-6-luna through the Portkey gateway, built once and shared. The Responses
API is used rather than chat/completions because this model needs it for
function tools.

Prompt caching: the provider caches a prompt prefix automatically once it is
long enough (about 1k tokens), and reports what it reused as cached input
tokens. Every agent therefore puts its stable system prompt first and the
changing conversation after it, so the cacheable prefix is as long as possible.
Nothing here asks for caching explicitly; the audit trail records whatever the
API reports.
"""

from __future__ import annotations

import os
from functools import lru_cache

from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from backend import config

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")


@lru_cache(maxsize=1)
def build_model() -> OpenAIResponsesModel:
    """One shared model instance, so the HTTP client and its pool are reused."""
    client = AsyncOpenAI(
        api_key=config.require_api_key(),
        base_url=config.PORTKEY_BASE_URL,
        default_headers={"x-portkey-provider": config.PORTKEY_PROVIDER},
        timeout=config.HTTP_TIMEOUT_S,
        max_retries=config.HTTP_MAX_RETRIES,
    )
    return OpenAIResponsesModel(
        config.MODEL_NAME, provider=OpenAIProvider(openai_client=client)
    )
