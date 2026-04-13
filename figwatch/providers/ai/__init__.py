"""AI provider protocol and factory.

All providers expose:
  .name         — display name used in sign-offs (e.g. 'Gemini', 'Claude')
  .inline_files — True if prompt embeds data inline; False if it uses file paths
  .call(prompt, image_path) -> str
"""

import os
import re
import time
from typing import Protocol, runtime_checkable

# Friendly aliases → full Anthropic API model IDs
CLAUDE_API_MODELS = {
    'sonnet': 'claude-sonnet-4-6',
    'opus':   'claude-opus-4-6',
    'haiku':  'claude-haiku-4-5-20251001',
}

# Friendly aliases → full Google AI model IDs
# Values not listed here are passed through as-is.
GEMINI_MODELS = {
    'gemini':            'gemini-3.1-flash-lite-preview',
    'gemini-flash':      'gemini-3.1-flash-lite-preview',
    'gemini-flash-lite': 'gemini-3.1-flash-lite-preview',
}


@runtime_checkable
class AIProvider(Protocol):
    name: str
    inline_files: bool

    def call(self, prompt: str, image_path: 'str | None') -> str:
        ...


def parse_retry_seconds(err, default=60):
    """Extract suggested retry delay in seconds from a 429 error message."""
    m = re.search(r'retry[_\s]delay\D*?(\d+)|retry after (\d+)', str(err), re.IGNORECASE)
    if m:
        return int(m.group(1) or m.group(2))
    return default


def with_retry(call_fn, is_rate_limit_fn, label):
    """Call call_fn(), retrying once on a rate-limit error after the suggested delay."""
    for attempt in range(2):
        try:
            return call_fn()
        except Exception as e:
            if is_rate_limit_fn(e) and attempt == 0:
                wait = parse_retry_seconds(e)
                print(f'   {label} 429 — retrying in {wait}s…', flush=True)
                time.sleep(wait)
            else:
                raise


def make_provider(model: str, claude_path: str, *, skill_dir: str = '') -> AIProvider:
    """Return the appropriate AI provider for the given model and claude_path."""
    from figwatch.providers.ai.gemini import GeminiProvider
    from figwatch.providers.ai.anthropic import AnthropicProvider
    from figwatch.providers.ai.claude_cli import ClaudeCLIProvider

    if (model or '').startswith('gemini'):
        model_name = GEMINI_MODELS.get(model, model)
        return GeminiProvider(model_name, os.environ.get('GOOGLE_API_KEY', ''))
    if claude_path == 'api':
        model_name = CLAUDE_API_MODELS.get(model, model)
        return AnthropicProvider(model_name, os.environ.get('ANTHROPIC_API_KEY', ''))
    return ClaudeCLIProvider(model, claude_path, skill_dir)
