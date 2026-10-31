"""
GhostShell: The Haunted AI Terminal.
A local, open-source cybersecurity terminal assistant powered by deterministic analysis
and local open-weight language models via Ollama.
"""

from ghostshell.command_analyzer import CommandSafetyAnalyzer
from ghostshell.ai_engine import OllamaAIEngine

__version__ = "1.0.0"
__all__ = ["CommandSafetyAnalyzer", "OllamaAIEngine"]
