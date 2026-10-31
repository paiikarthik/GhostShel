"""
Local AI Engine integration for GhostShell.
Interfaces directly with Ollama's local HTTP API (http://127.0.0.1:11434).
Zero cloud telemetry, zero paid APIs, 100% local and privacy-preserving.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Generator
import requests
from config import Config
from ghostshell.prompts import (
    build_chat_prompt,
    build_command_explanation_prompt,
    build_story_prompt
)
from ghostshell.spectral_engine import SpectralHeuristicEngine

logger = logging.getLogger(__name__)


class OllamaAIEngine:
    """
    Manages communication with the locally running Ollama instance.
    Handles model discovery, health checks, chat inference, and streaming.
    """

    OFFLINE_SETUP_GUIDE = (
        "GhostShell requires Ollama running locally for AI features.\n"
        "To awaken the ghost's voice:\n"
        "1. Install Ollama from https://ollama.com\n"
        "2. Pull an open-weight model: `ollama run qwen2.5:3b` (or `llama3.2:1b`)\n"
        "3. Ensure the service is running on http://127.0.0.1:11434"
    )

    def __init__(self, base_url: str = None, model: str = None, timeout: int = None):
        self.base_url = (base_url or Config.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or Config.OLLAMA_MODEL
        self.timeout = timeout if timeout is not None else Config.OLLAMA_TIMEOUT_SECONDS

    def check_status(self) -> Dict[str, Any]:
        """
        Queries Ollama's /api/tags endpoint to verify if the local daemon is active
        and checks if the configured model is installed.
        """
        # SSRF validation
        if not Config.validate_ollama_url(self.base_url):
            return {
                "available": False,
                "base_url": self.base_url,
                "current_model": self.model,
                "installed_models": [],
                "model_available": False,
                "error": f"Base URL '{self.base_url}' is not a permitted loopback address (SSRF protection).",
                "setup_guide": self.OFFLINE_SETUP_GUIDE
            }

        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                raw_models = data.get("models", [])
                
                # Format models list
                installed_models = []
                for m in raw_models:
                    installed_models.append({
                        "name": m.get("name"),
                        "size": m.get("size", 0),
                        "modified_at": m.get("modified_at", ""),
                        "details": m.get("details", {})
                    })

                installed_names = [m["name"] for m in installed_models]
                # Match full name (e.g. 'qwen2.5:3b') or base name without ':latest'
                model_match = any(
                    self.model == name or self.model == name.split(":")[0] or f"{self.model}:latest" == name
                    for name in installed_names
                )

                return {
                    "available": True,
                    "base_url": self.base_url,
                    "current_model": self.model,
                    "installed_models": installed_models,
                    "model_available": model_match,
                    "error": None if model_match else f"Model '{self.model}' is not in local Ollama storage.",
                    "setup_guide": None if model_match else f"Run: `ollama pull {self.model}` in your terminal."
                }
            else:
                return {
                    "available": False,
                    "base_url": self.base_url,
                    "current_model": self.model,
                    "installed_models": [],
                    "model_available": False,
                    "error": f"Ollama returned HTTP status {resp.status_code}.",
                    "setup_guide": self.OFFLINE_SETUP_GUIDE
                }
        except requests.exceptions.ConnectionError:
            return {
                "available": False,
                "base_url": self.base_url,
                "current_model": self.model,
                "installed_models": [],
                "model_available": False,
                "error": f"Cannot connect to Ollama at {self.base_url}. Service is offline or unreachable.",
                "setup_guide": self.OFFLINE_SETUP_GUIDE
            }
        except requests.exceptions.Timeout:
            return {
                "available": False,
                "base_url": self.base_url,
                "current_model": self.model,
                "installed_models": [],
                "model_available": False,
                "error": "Connection to Ollama timed out.",
                "setup_guide": self.OFFLINE_SETUP_GUIDE
            }
        except Exception as e:
            return {
                "available": False,
                "base_url": self.base_url,
                "current_model": self.model,
                "installed_models": [],
                "model_available": False,
                "error": f"Unexpected error while communicating with Ollama: {str(e)}",
                "setup_guide": self.OFFLINE_SETUP_GUIDE
            }

    def set_model(self, model_name: str) -> Dict[str, Any]:
        """
        Updates the active model identifier if valid.
        """
        self.model = model_name.strip()
        return self.check_status()

    def generate_chat_stream(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """
        Streams response tokens from Ollama's /api/chat endpoint using Server-Sent Events / NDJSON.
        Falls back seamlessly to the Spectral Heuristic Core when Ollama is offline.
        """
        status = self.check_status()
        if not status["available"]:
            user_msg = messages[-1].get("content", "") if messages else ""
            fallback_text = SpectralHeuristicEngine.answer_chat(user_msg)
            yield json.dumps({
                "type": "token",
                "content": fallback_text,
                "done": True
            }) + "\n"
            return

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9
            }
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=self.timeout
            )
            if resp.status_code != 200:
                yield json.dumps({
                    "type": "error",
                    "content": f"Ollama error (HTTP {resp.status_code}): {resp.text}",
                    "done": True
                }) + "\n"
                return

            for line in resp.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode("utf-8"))
                        msg = chunk.get("message", {})
                        token = msg.get("content", "")
                        is_done = chunk.get("done", False)

                        yield json.dumps({
                            "type": "token",
                            "content": token,
                            "done": is_done
                        }) + "\n"
                    except Exception as json_err:
                        logger.error(f"Error parsing Ollama stream chunk: {json_err}")
                        continue
        except requests.exceptions.Timeout:
            yield json.dumps({
                "type": "error",
                "content": "👻 *The neural connection drifted into the spectral abyss (Request Timed Out).* The model took too long to respond.",
                "done": True
            }) + "\n"
        except requests.exceptions.ConnectionError:
            yield json.dumps({
                "type": "error",
                "content": "👻 *The connection to Ollama broke abruptly.* Ensure Ollama is running.",
                "done": True
            }) + "\n"
        except Exception as e:
            yield json.dumps({
                "type": "error",
                "content": f"👻 Spectral transmission error: {str(e)}",
                "done": True
            }) + "\n"

    def generate_chat_sync(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Synchronous single-shot chat completion.
        Uses Ollama if online, or falls back to the Spectral Heuristic Core (0 MB Data required).
        """
        status = self.check_status()
        if not status["available"]:
            user_msg = messages[-1].get("content", "") if messages else ""
            fallback_text = SpectralHeuristicEngine.answer_chat(user_msg)
            return {
                "success": True,
                "content": fallback_text,
                "model": "spectral-heuristic-core",
                "eval_count": 0
            }

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7
            }
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            if resp.status_code == 200:
                data = resp.json()
                msg = data.get("message", {})
                return {
                    "success": True,
                    "content": msg.get("content", ""),
                    "model": self.model,
                    "eval_count": data.get("eval_count", 0)
                }
            else:
                return {
                    "success": False,
                    "content": f"GhostShell encountered an error from Ollama: HTTP {resp.status_code}.",
                    "error": resp.text,
                    "model": self.model
                }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "content": "👻 *The model took too long to awaken (Request Timed Out).* Try a smaller model or increase the timeout setting.",
                "error": "Request timed out",
                "model": self.model
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "content": "👻 *Connection to Ollama was refused.* Verify that Ollama is running.",
                "error": "Connection refused",
                "model": self.model
            }
        except Exception as e:
            return {
                "success": False,
                "content": f"Unexpected error: {str(e)}",
                "error": str(e),
                "model": self.model
            }

    def explain_command(self, command: str, analysis: Dict[str, Any], stream: bool = False):
        """
        Generates an AI explanation for a command while strictly preserving deterministic findings.
        Uses Ollama if online, or the built-in Spectral Heuristic Engine offline (0 MB Data required).
        """
        status = self.check_status()
        if not status["available"]:
            text = SpectralHeuristicEngine.explain_command(command, analysis)
            return {"success": True, "content": text, "model": "spectral-heuristic-core"}

        messages = build_command_explanation_prompt(command, analysis)
        if stream:
            return self.generate_chat_stream(messages)
        else:
            return self.generate_chat_sync(messages)

    def generate_story(self, params: Dict[str, Any], stream: bool = False):
        """
        Generates a fictional horror story or incident report via Haunted Archives.
        Uses Ollama if online, or procedural narrative generation offline (0 MB Data required).
        """
        status = self.check_status()
        if not status["available"]:
            story = SpectralHeuristicEngine.generate_procedural_story(params)
            return {"success": True, "content": story, "model": "spectral-heuristic-core"}

        messages = build_story_prompt(params)
        if stream:
            return self.generate_chat_stream(messages)
        else:
            return self.generate_chat_sync(messages)
