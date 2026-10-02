"""Provider-independent ports for book processing."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol


@dataclass
class ProviderReply:
    content: str = ""
    model: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input: int = 0
    cache_write: int = 0
    reasoning: int = 0
    characters: int = 0
    raw_usage: dict = field(default_factory=dict)
    request_id: str | None = None


class TextProvider(Protocol):
    name: str
    model: str

    def validate_model(self) -> None: ...

    def generate(self, system: str, payload: dict) -> ProviderReply: ...


class AudioProvider(Protocol):
    name: str
    model: str
    max_characters: int

    def generate(self, text: str, voice: str, destination: Path) -> ProviderReply: ...


class JsonGenerator(Protocol):
    def __call__(self, phase: str, system: str, payload: dict,
                 validate: Callable[[dict], None] | None = None) -> dict: ...


class ReductionStrategy(Protocol):
    key: str
    label: str

    def reduce(self, chapters: list[dict], options: dict, generate: JsonGenerator,
               progress: Callable[[int, str], None]) -> tuple[list[dict], list[str]]: ...
