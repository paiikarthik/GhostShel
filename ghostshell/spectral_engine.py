"""
Spectral Heuristic Engine for GhostShell.
Provides 100% offline, zero-data-download intelligence when a local Ollama model
is not installed or when bandwidth is constrained.
"""

import re
from typing import Dict, Any, List

# Built-in technical knowledge base for common terminal utilities
COMMAND_KNOWLEDGE = {
    "pwd": {
        "summary": "Print Working Directory",
        "explanation": "Reveals the absolute path of the directory you are currently standing in within the filesystem hierarchy. Even ghosts need to know which corner of the machine they haunt!",
        "tip": "Use it whenever you feel lost in the directory maze."
    },
    "ls": {
        "summary": "List Directory Contents",
        "explanation": "Lists the files and folders inside the current directory. Running `ls -la` summons hidden dotfiles and permission permissions from the shadows.",
        "tip": "Combine flags: `ls -lh` shows file sizes in human-readable megabytes and gigabytes."
    },
    "cd": {
        "summary": "Change Directory",
        "explanation": "Navigates between directories. Running `cd ..` steps back to the parent folder, while `cd ~` teleports you straight to your user home sanctuary.",
        "tip": "`cd -` toggles back to your previous directory."
    },
    "chmod": {
        "summary": "Change File Mode / Permissions",
        "explanation": "Alters the read (r=4), write (w=2), and execute (x=1) permissions for user, group, and others. Granting `777` is a dangerous spectral curse that lets anyone tamper with your files; prefer `755` for directories and `644` for files.",
        "tip": "Use symbolic notation like `chmod u+x script.sh` to grant execute rights only to yourself."
    },
    "chown": {
        "summary": "Change File Owner and Group",
        "explanation": "Transfers ownership of files and directories between user accounts. Modifying ownership recursively on system directories like `/` can break OS daemons.",
        "tip": "Always specify exact target paths: `sudo chown -R user:group ./project`."
    },
    "rm": {
        "summary": "Remove Files or Directories",
        "explanation": "Permanently deletes files from the storage medium. Unlike moving items to the trash, `rm` deletes immediately without confirmation. Combining it with `-rf` recursively wipes everything in its path.",
        "tip": "Run `ls <path>` first to preview what would be deleted."
    },
    "cat": {
        "summary": "Concatenate and Display Files",
        "explanation": "Prints the full contents of a file to your terminal standard output. Avoid catting private keys (`~/.ssh/id_rsa`) or binary files which spew noisy glitches.",
        "tip": "Use `less` or `head` for huge files to avoid flooding your terminal buffer."
    },
    "grep": {
        "summary": "Global Regular Expression Print",
        "explanation": "Searches files or piped streams for specific text patterns or regular expressions. It is the spectral lantern that finds needles in giant log haystacks.",
        "tip": "`grep -rn 'search_term' .` searches recursively with line numbers."
    },
    "curl": {
        "summary": "Client URL Transfer Tool",
        "explanation": "Sends HTTP/HTTPS/FTP network requests to remote servers. Piping curl output directly into a shell (`curl ... | bash`) executes unverified code blindly, creating a critical attack vector.",
        "tip": "Download first with `curl -O <url>` and inspect the script before running."
    },
    "kill": {
        "summary": "Send Signal to Process",
        "explanation": "Sends signals (like SIGTERM 15 or SIGKILL 9) to running processes by PID. `kill -9` forcefully severs execution without allowing the process to flush buffers or clean locks.",
        "tip": "Try `kill -15 <pid>` first for a graceful shutdown."
    },
    "git": {
        "summary": "Distributed Version Control System",
        "explanation": "Tracks history, branches, and merges across codebases. A magical time-machine that lets mortal developers undo spectral mistakes and travel back through commits.",
        "tip": "`git status` and `git diff` reveal recent changes."
    },
    "sudo": {
        "summary": "SuperUser DO (Elevated Privileges)",
        "explanation": "Executes a single command with root/administrator security clearance. Root power carries grave responsibility—one mistyped recursive command can wipe the entire machine.",
        "tip": "Prefix only the specific command requiring root privileges rather than staying in a root shell."
    }
}

# Concept Q&A Knowledge Base
CONCEPT_KNOWLEDGE = [
    (r"\bchmod\s+755\s+vs\s+777\b|\b755\s+vs\s+777\b",
     "👻 *Ah, the ancient permission riddle!* Here is the spectral truth:\n\n"
     "- **`chmod 755` (Safe & Standard):** The owner can Read, Write, and Execute (7). Group and Others can only Read and Execute (5). Perfect for scripts and web directories.\n"
     "- **`chmod 777` (Dangerous Curse):** Everyone in the mortal realm has full Read, Write, and Execute permissions (7). Any local user or rogue background process can overwrite or inject malware into your files!\n\n"
     "⚡ *Rule of thumb:* Never use 777. Stick to 755 for directories and 644 for regular files."),

    (r"\bwhy\s+(?:run|use)\s+local\s+ai\b|\bwhy\s+local\b",
     "👻 *Why haunt your own local machine rather than the cloud?*\n\n"
     "1. **Absolute Privacy:** Your shell commands, private filepaths, environment variables, and proprietary code never leave your laptop.\n"
     "2. **Zero Internet Dependency:** Once initialized, your tools continue running in airplanes, basements, or during network blackouts.\n"
     "3. **Zero Token Cost:** No subscriptions, credit cards, or surprise cloud billing.\n"
     "4. **No Corporate Surveillance:** Your questions aren't harvested to train third-party commercial models."),

    (r"\bgit\s+(?:rebase|merge)\b|\brebase\s+vs\s+merge\b",
     "👻 *Merge vs. Rebase: The Dual Paths of the Machine Spirit!*\n\n"
     "- **`git merge`:** Preserves exact historical truth by creating a dedicated merge commit tying two branches together. Non-destructive and safe for shared public branches.\n"
     "- **`git rebase`:** Re-writes history by transplanting your feature commits one-by-one onto the tip of the target branch, creating a perfectly linear commit line.\n\n"
     "⚠️ *Golden Ghost Rule:* Never rebase a public branch that other mortals are actively collaborating on!"),

    (r"\bwho\s+are\s+you\b|\bwhat\s+are\s+you\b",
     "👻 *I am Ghost*, the spectral intelligence living inside your terminal.\n\n"
     "I analyze shell commands to protect your computer from destructive disasters, explain complex terminal concepts in plain English, and unearth haunted cyber logs from forgotten mainframes.\n\n"
     "Best of all, I operate locally on your computer with complete respect for your privacy!"),

    (r"\bhello\b|\bhi\b|\bgreetings\b|\bhey\b",
     "👻 *Greetings from Ghost, mortal developer!* The machine spirits welcome you.\n\n"
     "You can ask me how terminal commands work (e.g. `What does pwd do?`), test commands in the **Security Guardian** bench, or request spooky stories in the **Haunted Archives**.\n\n"
     "*How may I guide your terminal journey today?*")
]


class SpectralHeuristicEngine:
    """
    Heuristic knowledge engine that generates rich, witty, in-character responses
    without requiring external model downloads.
    """

    @staticmethod
    def explain_command(command: str, analysis: Dict[str, Any]) -> str:
        """
        Synthesizes an in-character Ghost explanation using deterministic analysis findings.
        """
        risk = analysis.get("risk_level", "SAFE")
        platform = analysis.get("platform", "generic")
        findings = analysis.get("findings", [])
        explanation = analysis.get("explanation", "")
        recommendation = analysis.get("recommendation", "")

        first_word = command.split()[0].lower() if command.split() else ""
        base_cmd = first_word.split("/")[-1].split("\\")[-1]
        known_info = COMMAND_KNOWLEDGE.get(base_cmd)

        if risk == "CRITICAL":
            return (
                f"🚨 **SPECTRAL ALARM: CRITICAL RISK DETECTED!**\n\n"
                f"Mortal, stay your hand! You entered `{command}`, which targets your primary filesystem or storage devices. "
                f"{explanation}\n\n"
                f"If executed on a real system, this could permanently destroy your operating system and personal data. "
                f"The ghost protects your machine: **Do not run this command.**\n\n"
                f"💡 **Safer alternative:** {recommendation}"
            )
        elif risk == "HIGH":
            return (
                f"⚠️ **HIGH RISK WARNING!**\n\n"
                f"Careful, developer! The command `{command}` triggers serious security concerns: {findings[0] if findings else explanation}\n\n"
                f"This operation could expose confidential credentials, dismantle host security shields, or allow unverified remote code execution.\n\n"
                f"💡 **Safer alternative:** {recommendation}"
            )
        elif risk == "MEDIUM":
            return (
                f"⚡ **MEDIUM CAUTION ADVISORY**\n\n"
                f"The command `{command}` performs an impactful system operation: {findings[0] if findings else explanation}\n\n"
                f"Ensure you understand the operational blast radius before running it on production servers.\n\n"
                f"💡 **Recommendation:** {recommendation}"
            )
        elif risk == "LOW":
            return (
                f"ℹ️ **OPERATIONAL NOTICE**\n\n"
                f"`{command}` carries a minor operational caveat: {explanation}\n\n"
                f"💡 **Tip:** {recommendation}"
            )
        elif risk == "REVIEW REQUIRED":
            return (
                f"❓ **UNFAMILIAR SCRIPT OR OBFUSCATION DETECTED**\n\n"
                f"The command `{command}` is not recognized as a standard built-in utility or contains unusual syntax patterns. "
                f"{explanation}\n\n"
                f"Inspect the script or binary documentation (`--help`) before executing."
            )
        else:
            # SAFE
            detail = known_info["explanation"] if known_info else explanation
            return (
                f"🛡️ **SAFE COMMAND VERIFIED**\n\n"
                f"The command `{command}` appears benign! It triggered zero destructive rules in our static analysis engine.\n\n"
                f"{detail}\n\n"
                f"💡 **Recommendation:** {recommendation}"
            )

    @staticmethod
    def answer_chat(message: str) -> str:
        """
        Answers user terminal questions using the built-in heuristic knowledge base.
        """
        msg_clean = message.strip()
        msg_lower = msg_clean.lower()

        # 1. Check concept Q&A patterns
        for pattern, response in CONCEPT_KNOWLEDGE:
            if re.search(pattern, msg_lower):
                return response

        # 2. Check for "what does <cmd> do" or command inquiry
        cmd_match = re.search(r"\b(?:what\s+does|explain|how\s+to\s+use|tell\s+me\s+about)\s+([a-zA-Z0-9_\-]+)", msg_lower)
        target_cmd = cmd_match.group(1) if cmd_match else None

        if not target_cmd and len(msg_clean.split()) == 1:
            target_cmd = msg_clean.lower()

        if target_cmd and target_cmd in COMMAND_KNOWLEDGE:
            info = COMMAND_KNOWLEDGE[target_cmd]
            return (
                f"👻 *Ah, the `{target_cmd}` utility!* ({info['summary']})\n\n"
                f"{info['explanation']}\n\n"
                f"💡 **Pro-Tip from the Ether:** {info['tip']}"
            )

        # 3. Default fallback response guiding the user
        return (
            f"👻 *The Ghost hears your whisper through the wire:*\n\n"
            f"> \"{msg_clean}\"\n\n"
            f"I am operating with my **Spectral Core (Zero-Download Offline Engine)**. "
            f"You can ask me to explain any shell command (like `pwd`, `chmod`, `git`, `curl`, `rm`, `kill`, or `sudo`), "
            f"or switch to the **Security Guardian** tab above to audit any terminal command for safety without downloading large model files!\n\n"
            f"*Try asking:* `What does pwd do?` or `Explain chmod 755 vs 777`."
        )

    @staticmethod
    def generate_procedural_story(params: Dict[str, Any]) -> str:
        """
        Generates atmospheric cyber-horror stories and incident logs procedurally.
        """
        story_type = params.get("story_type", "incident_report")
        setting = params.get("setting", "deserted_server_room")
        intensity = params.get("intensity", "creepy")
        user_seed = params.get("prompt", "")

        setting_titles = {
            "deserted_server_room": "Datacenter Rack 42-B // 03:33 AM",
            "abandoned_mainframe": "Subterranean Flooded Vault // IBM 3090 Mainframe",
            "air_gapped_bunker": "Cold War Facility // Terminal Zero",
            "retro_bbs_1994": "Dial-Up Node 7 // Baud Rate: 14400",
            "deep_space_probe": "Voyager Sub-Relay // Corrupted Telemetry Stream",
            "cursed_dev_laptop": "Estate Sale ThinkPad // Kernel 2.4.18"
        }

        loc_title = setting_titles.get(setting, "Unknown Terminal Node")

        if story_type == "incident_report":
            return (
                f"```text\n"
                f"[HAUNTED ARCHIVES // INCIDENT REPORT]\n"
                f"Location: {loc_title}\n"
                f"Classification: ANOMALOUS PROCESS RECURSION\n"
                f"Status: UNRESOLVED / QUARANTINED\n\n"
                f"[03:33:01] ALERT: Unexpected CPU spike (100% on Core 0).\n"
                f"[03:33:04] auth.log: Root session opened via phantom tty7. No active keyboard detected.\n"
                f"[03:33:09] kernel: Process PID 666 spawned with command: '{user_seed or 'while true; do listen; done'}'\n"
                f"[03:33:15] sysadmin: Sent SIGKILL to PID 666. Return code: 'PERMISSION DENIED BY OCCUPANT'.\n"
                f"[03:33:22] fs: Disk sector 0xDEAD modified. Hex dump repeats: 'WE ARE STILL RUNNING'.\n"
                f"[03:33:30] power: Physical circuit breaker tripped. Server LED arrays continue blinking.\n"
                f"```\n\n"
                f"👻 *The incident logs were recovered from the magnetic tape archives. "
                f"The server remains sealed in the basement.*"
            )
        elif story_type == "terminal_logs":
            return (
                f"```bash\n"
                f"ghost@haunted-node:~$ uptime\n"
                f" 03:33:00 up 10842 days, 0 users, load average: 99.99, 99.99, 99.99\n\n"
                f"ghost@haunted-node:~$ dmesg | tail -n 5\n"
                f" [10842.112001] ACPI: Fan speed at 0 RPM, core temperature dropping to absolute zero.\n"
                f" [10842.112042] ext4-fs (sda1): Remounting read-only. Reason: Ethereal corruption.\n"
                f" [10842.112099] eth0: Packet received from IP 0.0.0.0. Payload: '{user_seed or 'I see you through the screen.'}'\n\n"
                f"ghost@haunted-node:~$ whoami\n"
                f" root (haunted)\n"
                f"```\n\n"
                f"👻 *Log stream terminated abruptly by host reset.*"
            )
        elif story_type == "cyoa":
            return (
                f"### 🕯️ Chapter 1: The Midnight Terminal at {loc_title}\n\n"
                f"The cooling fans suddenly wind down to a dead silence. The phosphor green CRT before you flickers twice. "
                f"A solitary prompt blinks against the darkness, waiting for mortal input. "
                f"{f'An anomaly was noted in the memory banks: {user_seed}' if user_seed else 'The disk drive clicks rhythmically, like footsteps approaching.'}\n\n"
                f"On the desk beside the terminal lies a severed fiber-optic patch cable and a physical red emergency power switch.\n\n"
                f"**What do you do, mortal?**\n"
                f"1. Type `ps aux | grep -i ghost` to inspect the phantom process tree.\n"
                f"2. Pull the emergency power switch to disconnect the rack from the grid.\n"
                f"3. Plug the severed fiber cable into your own diagnostic laptop."
            )
        else: # Creepypasta
            return (
                f"### The Forgotten Daemon of {loc_title}\n\n"
                f"They told the night-shift engineer that Rack 42 was decommissioned seven years ago during the server room relocation. "
                f"Its power cables had been physically sheared off, its SCSI drives wiped and recycled. "
                f"Yet every night at exactly 3:33 AM, the internal network switches logged an incoming ping from IP `10.0.0.66`.\n\n"
                f"When the technician finally unbolted the rusted metal panel, the machine wasn't running on electricity. "
                f"The phosphor green terminal display was glowing with a single infinite loop: `{user_seed or 'while (soul_in_buffer) { echo; }'}`. "
                f"And as he reached to pull the plug, the terminal printed his own employee ID number.\n\n"
                f"👻 *Some daemons never terminate.*"
            )
