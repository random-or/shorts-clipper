"""Typed exceptions used across the clipping pipeline."""


class ShortsClipperError(Exception):
    """Base class for all project-specific exceptions."""


class ConfigurationError(ShortsClipperError):
    """Raised when settings or credentials are invalid."""


class ProviderError(ShortsClipperError):
    """Raised when an AI provider fails or returns invalid output."""


class MediaProcessingError(ShortsClipperError):
    """Raised when ffmpeg/movie processing fails."""
