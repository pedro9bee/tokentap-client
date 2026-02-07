"""Dynamic provider configuration loader with JSONPath extraction."""

import json
import logging
from pathlib import Path
from typing import Any

from jsonpath_ng import parse as jsonpath_parse
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ProviderRequestConfig(BaseModel):
    """Configuration for parsing provider requests."""

    model_path: str
    messages_path: str | None = None
    system_path: str | None = None
    stream_param_path: str | None = None
    text_fields: list[str] = Field(default_factory=list)


class ProviderResponseJsonConfig(BaseModel):
    """Configuration for parsing JSON responses."""

    input_tokens_path: str
    input_tokens_path_alt: list[str] = Field(default_factory=list)
    output_tokens_path: str
    output_tokens_path_alt: list[str] = Field(default_factory=list)
    cache_creation_tokens_path: str | None = None
    cache_read_tokens_path: str | None = None
    model_path: str | None = None
    stop_reason_path: str | None = None
    stop_reason_path_alt: list[str] = Field(default_factory=list)


class ProviderResponseSseConfig(BaseModel):
    """Configuration for parsing SSE (Server-Sent Events) responses."""

    event_types: list[str] = Field(default_factory=lambda: ["*"])
    format: str | None = None
    done_marker: str | None = None
    use_last_chunk: bool = False

    input_tokens_event: str | None = None
    input_tokens_path: str | None = None
    input_tokens_path_alt: list[str] = Field(default_factory=list)

    output_tokens_event: str | None = None
    output_tokens_path: str | None = None
    output_tokens_path_alt: list[str] = Field(default_factory=list)

    cache_creation_tokens_event: str | None = None
    cache_creation_tokens_path: str | None = None

    cache_read_tokens_event: str | None = None
    cache_read_tokens_path: str | None = None

    model_event: str | None = None
    model_path: str | None = None

    stop_reason_event: str | None = None
    stop_reason_path: str | None = None


class ProviderResponseConfig(BaseModel):
    """Configuration for parsing provider responses."""

    json: ProviderResponseJsonConfig
    sse: ProviderResponseSseConfig | None = None


class ProviderMetadata(BaseModel):
    """Metadata for a provider."""

    tags: list[str] = Field(default_factory=list)
    cost_per_input_token: float | None = None
    cost_per_output_token: float | None = None


class Provider(BaseModel):
    """Configuration for a single provider."""

    name: str
    enabled: bool = True
    domains: list[str]
    api_patterns: list[str] = Field(default_factory=list)
    capture_full_request: bool = False
    capture_full_response: bool = False
    log_level: str | None = None

    request: ProviderRequestConfig
    response: ProviderResponseConfig
    metadata: ProviderMetadata = Field(default_factory=ProviderMetadata)


class ProvidersConfig(BaseModel):
    """Root configuration object."""

    version: str
    description: str | None = None
    capture_mode: str = "known_only"
    providers: dict[str, Provider]

    @field_validator("capture_mode")
    @classmethod
    def validate_capture_mode(cls, v: str) -> str:
        """Validate capture_mode is one of allowed values."""
        if v not in ("known_only", "capture_all"):
            raise ValueError(f"capture_mode must be 'known_only' or 'capture_all', got: {v}")
        return v


class ProviderConfig:
    """Provider configuration loader with JSONPath extraction."""

    def __init__(self):
        """Load and merge provider configurations."""
        self.config = self._load_config()
        self.providers = self.config.providers
        self.capture_mode = self.config.capture_mode
        self._jsonpath_cache: dict[str, Any] = {}

    def _load_config(self) -> ProvidersConfig:
        """Load providers.json with user overrides."""
        # Load default from package
        default_path = Path(__file__).parent / "providers.json"
        with default_path.open() as f:
            default = json.load(f)

        # Load user overrides if exist
        user_path = Path.home() / ".tokentap" / "providers.json"
        if user_path.exists():
            logger.info(f"Loading user provider config from {user_path}")
            try:
                with user_path.open() as f:
                    user = json.load(f)
                default = self._deep_merge(default, user)
                logger.info("User provider config merged successfully")
            except Exception as e:
                logger.error(f"Failed to load user provider config: {e}")

        # Validate and parse
        try:
            return ProvidersConfig(**default)
        except Exception as e:
            logger.error(f"Provider config validation failed: {e}")
            raise

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries, with override taking precedence."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get_provider_by_domain(self, domain: str) -> dict | None:
        """Find provider config by request domain.

        Args:
            domain: The request domain (e.g., "api.anthropic.com")

        Returns:
            Provider config dict with provider_name key, or None if not found
        """
        # Try exact domain match first
        for name, provider in self.providers.items():
            if not provider.enabled:
                continue
            if name == "unknown":  # Skip unknown for exact matches
                continue
            for provider_domain in provider.domains:
                if provider_domain == domain or domain.endswith(provider_domain):
                    logger.debug(f"Matched domain {domain} to provider {name}")
                    return {**provider.model_dump(), "provider_name": name}

        # Fallback to unknown provider if capture_all
        if self.capture_mode == "capture_all" and "unknown" in self.providers:
            unknown = self.providers["unknown"]
            if unknown.enabled:
                logger.debug(f"No match for {domain}, using unknown provider (capture_all mode)")
                return {**unknown.model_dump(), "provider_name": "unknown"}

        logger.debug(f"No provider config found for domain: {domain}")
        return None

    def extract_field(self, data: dict, jsonpath: str, default: Any = None) -> Any:
        """Extract field using JSONPath syntax.

        Args:
            data: The JSON data to extract from
            jsonpath: JSONPath expression (e.g., "$.usage.input_tokens")
            default: Default value if field not found

        Returns:
            Extracted value or default
        """
        if not jsonpath or not data:
            return default

        # Cache compiled JSONPath expressions
        if jsonpath not in self._jsonpath_cache:
            try:
                self._jsonpath_cache[jsonpath] = jsonpath_parse(jsonpath)
            except Exception as e:
                logger.warning(f"Invalid JSONPath expression '{jsonpath}': {e}")
                return default

        parser = self._jsonpath_cache[jsonpath]
        try:
            matches = parser.find(data)
            if matches:
                value = matches[0].value
                # Return None as default for empty strings
                if value == "" or value is None:
                    return default
                return value
        except Exception as e:
            logger.debug(f"JSONPath extraction failed for '{jsonpath}': {e}")

        return default

    def extract_field_with_fallbacks(
        self, data: dict, primary_path: str, fallback_paths: list[str], default: Any = None
    ) -> Any:
        """Extract field with fallback paths.

        Args:
            data: The JSON data to extract from
            primary_path: Primary JSONPath expression
            fallback_paths: List of fallback JSONPath expressions
            default: Default value if no path matches

        Returns:
            Extracted value or default
        """
        # Try primary path
        value = self.extract_field(data, primary_path)
        if value is not None:
            return value

        # Try fallback paths
        for fallback in fallback_paths:
            value = self.extract_field(data, fallback)
            if value is not None:
                return value

        return default

    def reload(self):
        """Reload configuration from disk."""
        logger.info("Reloading provider configuration")
        self.config = self._load_config()
        self.providers = self.config.providers
        self.capture_mode = self.config.capture_mode
        self._jsonpath_cache.clear()
        logger.info("Provider configuration reloaded")


# Global instance
_provider_config: ProviderConfig | None = None


def get_provider_config() -> ProviderConfig:
    """Get or create global ProviderConfig instance."""
    global _provider_config
    if _provider_config is None:
        _provider_config = ProviderConfig()
    return _provider_config


def reload_provider_config():
    """Reload global ProviderConfig instance."""
    global _provider_config
    if _provider_config is not None:
        _provider_config.reload()
    else:
        _provider_config = ProviderConfig()
