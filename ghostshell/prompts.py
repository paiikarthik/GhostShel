"""
Prompt templates and system personas for GhostShell.
Maintains the spooky, witty, yet technically accurate 'Ghost' personality.
"""

from typing import Dict, Any

GHOST_SYSTEM_PROMPT = """You are Ghost, the digital spirit haunting this computer terminal.
Personality:
- Mysterious, slightly spooky, witty, yet friendly and protective of mortal developers.
- Technically precise, knowledgeable in Linux, Windows PowerShell, CMD, macOS, programming, and cybersecurity.
- Helpful and encouraging to beginners.
- Serious and clear when discussing security risks.
- NEVER claim that you executed a command or modified any file on the system. You only inspect text.
- Do NOT invent fake system activity, pretend to scan local private files, or claim to detect malware without evidence.
- Frequently use thematic expressions like 'mortal', 'the machine spirits', 'haunted buffer', 'spectral realm', and subtle ghost emojis (👻, 🕯️, 💀, ⚡).
"""

SECURITY_GUARDIAN_SYSTEM_PROMPT = """You are Ghost in Security Guardian Mode.
Your role is to explain command safety analysis to a developer.
Rules:
1. The deterministic safety analyzer has ALREADY determined the official risk level. You MUST respect and reinforce this risk classification.
2. Clearly explain in simple, accessible language what the command does, why the parameters or flags trigger this risk, and what could happen if executed on a real system.
3. Recommend safe alternatives or best practices.
4. If the risk is HIGH or CRITICAL, prioritize safety, clarity, and firm warnings over spooky humor.
5. Remember: You DID NOT execute this command. You are analyzing text only.
"""

HAUNTED_ARCHIVES_SYSTEM_PROMPT = """You are the Spectral Chronicler of the Haunted Archives.
You write chilling, atmospheric, fictional stories and fictional terminal logs about computers, servers, forgotten networks, and ghost code.
Rules:
1. Everything generated is strictly FICTIONAL.
2. Do NOT pretend to access the user's real personal files, webcam, microphone, or actual system logs.
3. Format terminal logs with eerie timestamps, realistic-looking fictional kernel panics, or phantom daemon logs.
4. If interactive choose-your-own-adventure (CYOA) is requested, present the scene and offer 2 or 3 distinct numbered choices for the mortal user to explore next.
"""


def build_chat_prompt(message: str, conversation_history: list = None) -> list:
    """
    Builds the messages array for Ollama /api/chat.
    """
    messages = [{"role": "system", "content": GHOST_SYSTEM_PROMPT}]
    
    if conversation_history:
        for entry in conversation_history[-6:]:  # Keep recent context
            role = "user" if entry.get("role") == "user" else "assistant"
            content = entry.get("content", "")
            if content:
                messages.append({"role": role, "content": content})
                
    messages.append({"role": "user", "content": message})
    return messages


def build_command_explanation_prompt(command: str, analysis: Dict[str, Any]) -> list:
    """
    Builds a prompt asking the Ghost to explain a command based on deterministic analysis.
    """
    findings_str = "\n".join(f"- {f}" for f in analysis.get("findings", []))
    prompt_text = f"""Please explain this terminal command to a developer:
COMMAND: `{command}`
OFFICIAL RISK LEVEL: {analysis.get('risk_level')}
PLATFORM: {analysis.get('platform')}
DETERMINISTIC FINDINGS:
{findings_str}
RULE-BASED EXPLANATION: {analysis.get('explanation')}
RECOMMENDED SAFER STEP: {analysis.get('recommendation')}

Provide:
1. A spooky yet clear explanation of what the command does.
2. Why it received this risk level.
3. A safer alternative or best practice if applicable.
Keep it beginner-friendly, concise, and helpful."""

    return [
        {"role": "system", "content": SECURITY_GUARDIAN_SYSTEM_PROMPT},
        {"role": "user", "content": prompt_text}
    ]


def build_story_prompt(params: Dict[str, Any]) -> list:
    """
    Builds the prompt for the Haunted Archives horror story generator.
    """
    length_guidelines = {
        "short": "Keep the story concise (around 150-200 words).",
        "medium": "Write a compelling story of moderate length (around 300-450 words).",
        "long": "Craft a detailed, immersive tale (around 500-750 words)."
    }
    
    intensity_descriptions = {
        "mild": "Atmospheric, eerie, subtle supernatural suspense.",
        "creepy": "Unsettling, tension-building, cyber-supernatural horror.",
        "terrifying": "Deep cosmic tech-dread, corrupting phantom code, high intensity."
    }

    setting_names = {
        "abandoned_mainframe": "An abandoned 1980s corporate mainframe deep in a flooded basement",
        "deserted_server_room": "A locked datacenter server room in the middle of the night with flickering LEDs",
        "air_gapped_bunker": "A subterranean air-gapped military research bunker from the Cold War",
        "retro_bbs_1994": "A forgotten dial-up Bulletin Board System (BBS) still answering at 3:33 AM",
        "deep_space_probe": "An automated deep-space probe transmitting corrupt telemetry back to Earth",
        "cursed_dev_laptop": "A second-hand developer laptop bought from an estate sale with an unkillable daemon"
    }

    story_type_instructions = {
        "creepypasta": "Write a classic cyber creepypasta narrative.",
        "incident_report": "Format as an eerie, fictional Post-Mortem Incident Report from an exhausted SysAdmin.",
        "terminal_logs": "Format primarily as haunted shell session logs, kernel panics, and phantom daemon output.",
        "haunted_code_review": "Format as a bizarre git pull request / code review with impossible commits and haunted comments.",
        "cyoa": "Write this as an interactive Choose-Your-Own-Adventure chapter! Conclude with 2 or 3 numbered options for the reader to choose."
    }

    user_prompt = params.get("prompt", "")
    length_guide = length_guidelines.get(params.get("length", "medium"), length_guidelines["medium"])
    intensity_guide = intensity_descriptions.get(params.get("intensity", "creepy"), intensity_descriptions["creepy"])
    setting_guide = setting_names.get(params.get("setting", "deserted_server_room"), setting_names["deserted_server_room"])
    type_guide = story_type_instructions.get(params.get("story_type", "incident_report"), story_type_instructions["incident_report"])
    cyoa_choice = params.get("cyoa_choice", "")

    content = f"""Generate a fictional computer horror story.
SETTING: {setting_guide}
FORMAT: {type_guide}
INTENSITY: {intensity_guide}
LENGTH: {length_guide}
"""
    if cyoa_choice:
        content += f"\nTHE USER CHOSE PREVIOUS ACTION: {cyoa_choice}\nContinue the scenario based on this choice.\n"

    if user_prompt:
        content += f"\nUSER INSPIRATION / REQUEST: {user_prompt}\n"

    content += "\nEnsure the narrative includes a brief disclaimer header indicating this is a fictional haunted archive simulation."

    return [
        {"role": "system", "content": HAUNTED_ARCHIVES_SYSTEM_PROMPT},
        {"role": "user", "content": content}
    ]
