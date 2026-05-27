"""Application settings with lightweight `.env` support."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('\"').strip("'")
        if key:
            values[key] = value
    return values


def _env(name: str, file_values: dict[str, str], default: str | None = None) -> str | None:
    return os.environ.get(name) or file_values.get(name) or default


@dataclass(frozen=True, slots=True)
class Settings:
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    default_provider: str = "gemini"
    whisper_model: str = "tiny.en"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    models_dir: Path = Path("models")
    output_dir: Path = Path("outputs")
    cache_dir: Path = Path(".cache/shorts-clipper")
    log_level: str = "INFO"
    enable_gpu: bool = False

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> Settings:
        path = Path(env_path)
        file_values = _parse_env_file(path)
        return cls(
            gemini_api_key=_env("GEMINI_API_KEY", file_values),
            openai_api_key=_env("OPENAI_API_KEY", file_values),
            anthropic_api_key=_env("ANTHROPIC_API_KEY", file_values),
            ollama_base_url=_env("OLLAMA_BASE_URL", file_values, "http://localhost:11434") or "http://localhost:11434",
            default_provider=_env("SHORTS_PROVIDER", file_values, "gemini") or "gemini",
            whisper_model=_env("SHORTS_WHISPER_MODEL", file_values, "tiny.en") or "tiny.en",
            whisper_device=_env("SHORTS_WHISPER_DEVICE", file_values, "cpu") or "cpu",
            whisper_compute_type=_env("SHORTS_WHISPER_COMPUTE_TYPE", file_values, "int8") or "int8",
            models_dir=Path(_env("SHORTS_MODELS_DIR", file_values, "models") or "models"),
            output_dir=Path(_env("SHORTS_OUTPUT_DIR", file_values, "outputs") or "outputs"),
            cache_dir=Path(
                _env("SHORTS_CACHE_DIR", file_values, ".cache/shorts-clipper")
                or ".cache/shorts-clipper"
            ),
            log_level=(_env("SHORTS_LOG_LEVEL", file_values, "INFO") or "INFO").upper(),
            enable_gpu=(
                (_env("SHORTS_ENABLE_GPU", file_values, "false") or "false")
                .lower() in {"1", "true", "yes", "on"}
            ),
        )
