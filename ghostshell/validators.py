"""
Input validation and sanitization for GhostShell.
Provides defensive checks to prevent malformed data, injection, and resource exhaustion.
"""

import re
from typing import Tuple, Optional, Any

# Allowed story parameters
VALID_STORY_LENGTHS = {"short", "medium", "long"}
VALID_INTENSITIES = {"mild", "creepy", "terrifying"}
VALID_SETTINGS = {
    "abandoned_mainframe",
    "deserted_server_room",
    "air_gapped_bunker",
    "retro_bbs_1994",
    "deep_space_probe",
    "cursed_dev_laptop"
}
VALID_STORY_TYPES = {
    "creepypasta",
    "incident_report",
    "terminal_logs",
    "haunted_code_review",
    "cyoa"
}

# Regex for valid model names (e.g., qwen2.5:3b, llama3.2:1b, mistral:7b, custom-model:latest)
MODEL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.:/]+$")


def sanitize_text(text: Any, max_length: int = 4000) -> str:
    """
    Sanitizes string input by removing null bytes, ensuring string type,
    and enforcing a maximum character length limit.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    # Remove null bytes which can cause issues in C-based libraries
    text = text.replace("\x00", "")
    # Trim to max length
    return text[:max_length].strip()


def validate_command_input(command: Any) -> Tuple[bool, str, Optional[str]]:
    """
    Validates a command input for analysis.
    Returns: (is_valid, sanitized_command, error_message)
    """
    if command is None:
        return False, "", "Command cannot be null."
    if not isinstance(command, str):
        return False, "", "Command must be a string."
    
    sanitized = sanitize_text(command, max_length=2048)
    if not sanitized:
        return False, "", "Command cannot be empty or purely whitespace."
    
    return True, sanitized, None


def validate_chat_input(message: Any) -> Tuple[bool, str, Optional[str]]:
    """
    Validates a user message for interactive terminal chat.
    Returns: (is_valid, sanitized_message, error_message)
    """
    if message is None:
        return False, "", "Message cannot be null."
    if not isinstance(message, str):
        return False, "", "Message must be a string."
    
    sanitized = sanitize_text(message, max_length=4096)
    if not sanitized:
        return False, "", "Message cannot be empty."
    
    return True, sanitized, None


def validate_story_params(data: dict) -> Tuple[bool, dict, Optional[str]]:
    """
    Validates parameters for the Haunted Archives story generator.
    Returns: (is_valid, sanitized_params_dict, error_message)
    """
    if not isinstance(data, dict):
        return False, {}, "Request body must be a JSON object."
    
    prompt = sanitize_text(data.get("prompt", ""), max_length=1000)
    length = str(data.get("length", "medium")).lower().strip()
    intensity = str(data.get("intensity", "creepy")).lower().strip()
    setting = str(data.get("setting", "deserted_server_room")).lower().strip()
    story_type = str(data.get("story_type", "incident_report")).lower().strip()
    cyoa_choice = sanitize_text(data.get("cyoa_choice", ""), max_length=500)

    if length not in VALID_STORY_LENGTHS:
        length = "medium"
    if intensity not in VALID_INTENSITIES:
        intensity = "creepy"
    if setting not in VALID_SETTINGS:
        setting = "deserted_server_room"
    if story_type not in VALID_STORY_TYPES:
        story_type = "incident_report"

    params = {
        "prompt": prompt,
        "length": length,
        "intensity": intensity,
        "setting": setting,
        "story_type": story_type,
        "cyoa_choice": cyoa_choice
    }
    return True, params, None


def validate_model_name(name: Any) -> Tuple[bool, str, Optional[str]]:
    """
    Validates a requested model identifier.
    Returns: (is_valid, sanitized_model_name, error_message)
    """
    if not name or not isinstance(name, str):
        return False, "", "Model name must be a non-empty string."
    
    cleaned = name.strip()
    if len(cleaned) > 100:
        return False, "", "Model name is too long."
    
    if not MODEL_NAME_PATTERN.match(cleaned):
        return False, "", "Model name contains invalid characters."
    
    return True, cleaned, None
