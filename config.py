"""
Configuration module for GhostShell: The Haunted AI Terminal.
Handles environment variables, security constraints, and runtime settings.
"""

import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()


class Config:
    """Base application configuration."""

    # Server binding (Default: strictly local loopback for privacy)
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("DEBUG", "False").strip().lower() in ("true", "1", "yes")

    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "ghostshell-spectral-cipher-default-key-change-me")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 64 * 1024))  # 64 KB limit

    # Local AI Runtime (Ollama)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "30"))

    # SSRF Protection: List of allowed loopback hosts for Ollama
    ALLOWED_OLLAMA_HOSTS = {"127.0.0.1", "localhost", "::1", "[::1]"}

    @classmethod
    def validate_ollama_url(cls, url: str) -> bool:
        """
        Validate the Ollama endpoint URL to prevent Server-Side Request Forgery (SSRF).
        Only loopback addresses (localhost/127.0.0.1) are permitted by default.
        """
        if not url:
            return False
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            hostname = parsed.hostname or ""
            return hostname.lower() in cls.ALLOWED_OLLAMA_HOSTS
        except Exception:
            return False


class TestingConfig(Config):
    """Configuration used during automated tests."""
    TESTING = True
    DEBUG = False
    OLLAMA_TIMEOUT_SECONDS = 2
