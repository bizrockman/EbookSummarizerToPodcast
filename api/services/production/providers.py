"""Composition root and OpenAI adapters. Domain services do not import the SDK."""
import json
from pathlib import Path
from api.config.settings import settings
from .contracts import ProviderReply
from .strategies import StrategyRegistry, BlockReadingStrategy, TopicCoreStrategy


class ProviderValidationError(ValueError):
    def __init__(self, message, status_code=422):
        super().__init__(message)
        self.status_code = status_code


class OpenAITextProvider:
    name = "openai"

    def __init__(self, model, client=None):
        from openai import OpenAI
        self.model = model
        self.client = client or OpenAI(api_key=settings.openai_api_key, timeout=240, max_retries=0)

    def validate_model(self):
        """Read-only availability check. Sends no book text and generates no tokens."""
        from openai import APIConnectionError, APIStatusError
        try:
            self.client.with_options(timeout=20).models.retrieve(self.model)
        except APIConnectionError as exc:
            raise ProviderValidationError("OpenAI ist nicht erreichbar. Prüfe die Internetverbindung "
                "und die Netzwerkberechtigung des API-Prozesses und des Workers.", 503) from exc
        except APIStatusError as exc:
            if exc.status_code == 404:
                raise ProviderValidationError(f"Das API-Modell '{self.model}' ist für diesen Zugang nicht verfügbar. "
                    "Prüfe den exakten API-Modellnamen, zum Beispiel gpt-5 oder gpt-6.1-sol.") from exc
            raise ProviderValidationError(f"Die OpenAI-Modellprüfung wurde abgelehnt (HTTP {exc.status_code}). "
                "Prüfe den API-Zugang und seine Berechtigungen.", 503) from exc

    def generate(self, system, payload):
        kwargs = {"reasoning_effort": "low"} if self.model.startswith(("gpt-5", "gpt-6", "o3", "o4")) else {}
        response = self.client.chat.completions.create(model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            response_format={"type": "json_object"}, max_completion_tokens=12000, **kwargs)
        usage = response.usage
        raw = usage.model_dump() if usage else {}
        reply = ProviderReply(content=response.choices[0].message.content or "", model=response.model,
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
            cached_input=(raw.get("prompt_tokens_details") or {}).get("cached_tokens") or 0,
            cache_write=(raw.get("prompt_tokens_details") or {}).get("cache_write_tokens") or 0,
            reasoning=(raw.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0,
            raw_usage=raw, request_id=response.id)
        # The meter records usage before JSON validation, including incomplete replies.
        if response.choices[0].finish_reason != "stop":
            reply.content = ""
        return reply


class OpenAIAudioProvider:
    name = "openai"
    max_characters = 4000

    def __init__(self, model, client=None):
        from openai import OpenAI
        self.model = model
        self.client = client or OpenAI(api_key=settings.openai_api_key, timeout=240, max_retries=0)

    def generate(self, text, voice, destination: Path):
        response = self.client.audio.speech.create(model=self.model, input=text, voice=voice,
                                                   response_format="mp3", speed=1.0)
        response.write_to_file(str(destination))
        return ProviderReply(model=self.model, characters=len(text))


class ProviderRegistry:
    def __init__(self, text_factories, audio_factories):
        self.text_factories = text_factories
        self.audio_factories = audio_factories

    def text(self, provider, model):
        if provider not in self.text_factories:
            raise ValueError("Textanbieter nicht verfügbar: " + provider)
        return self.text_factories[provider](model)

    def audio(self, provider, model):
        if provider not in self.audio_factories:
            raise ValueError("Audioanbieter nicht verfügbar: " + provider)
        return self.audio_factories[provider](model)


def get_providers():
    return ProviderRegistry({"openai": OpenAITextProvider}, {"openai": OpenAIAudioProvider})


def get_strategies():
    return StrategyRegistry([BlockReadingStrategy(), TopicCoreStrategy()])
