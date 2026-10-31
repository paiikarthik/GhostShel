"""
Deterministic Command Safety Analyzer for GhostShell.
Performs platform-aware static analysis of shell commands without executing them.
Categorizes risks into CRITICAL, HIGH, MEDIUM, LOW, SAFE, or REVIEW REQUIRED.
"""

import re
import shlex
from typing import Dict, List, Any, Tuple
from ghostshell.risk_rules import RULES, OBFUSCATION_PATTERNS, CHAINING_OPERATORS


class CommandSafetyAnalyzer:
    """
    Deterministic static security analyzer for terminal commands.
    Analyzes command syntax, dangerous flags, destructive targets,
    subshells, and obfuscation.
    """

    # Safe built-ins and common utility commands (all lowercase for robust matching)
    BENIGN_COMMANDS = {
        "ls", "dir", "pwd", "cd", "echo", "cat", "more", "less", "head", "tail",
        "whoami", "hostname", "uname", "date", "cal", "uptime", "ps", "top", "htop",
        "git", "python", "python3", "py", "node", "npm", "pnpm", "yarn", "cargo",
        "gcc", "g++", "make", "cmake", "docker", "kubectl", "grep", "findstr",
        "which", "where", "man", "help", "clear", "cls", "df", "du", "free",
        "touch", "mkdir", "cp", "mv", "tree", "wc", "sort", "uniq", "diff",
        "ping", "traceroute", "tracert", "nslookup", "dig", "ipconfig", "ifconfig",
        "get-process", "get-service", "get-childitem", "get-date", "get-location",
        "write-host", "write-output", "test-path", "select-string", "measure-object",
        "rm", "del", "remove-item"
    }

    RISK_HIERARCHY = {
        "CRITICAL": 5,
        "HIGH": 4,
        "MEDIUM": 3,
        "REVIEW REQUIRED": 2,
        "LOW": 1,
        "SAFE": 0
    }

    def __init__(self):
        # Pre-compile rule regular expressions for efficiency
        self.compiled_rules = []
        for rule in RULES:
            compiled_patterns = [
                re.compile(p, re.IGNORECASE | re.MULTILINE) for p in rule["patterns"]
            ]
            self.compiled_rules.append({**rule, "compiled_patterns": compiled_patterns})

        self.compiled_obfuscation = [
            (re.compile(p, re.IGNORECASE), desc) for p, desc in OBFUSCATION_PATTERNS
        ]

    def detect_platform(self, command: str) -> str:
        """
        Infers the target shell or operating system platform from command syntax.
        """
        cmd_lower = command.lower()
        
        # PowerShell signatures
        if any(term in cmd_lower for term in [
            "get-", "set-", "remove-item", "start-process", "stop-process",
            "invoke-expression", "invoke-webrequest", "iwr", "iex",
            "-recurse", "-force", "$env:", "$true", "$false"
        ]):
            return "windows_powershell"

        # Windows CMD signatures
        if any(term in cmd_lower for term in [
            "rmdir /s", "del /f", "rd /s", "format ", "taskkill /f",
            "netsh advfirewall", "net localgroup", "cls", "%userprofile%"
        ]):
            return "windows_cmd"

        # macOS specific
        if any(term in cmd_lower for term in ["brew ", "defaults write", "launchctl", "pbcopy", "pbpaste"]):
            return "macos"

        # Linux / Unix signatures
        if any(term in cmd_lower for term in [
            "sudo", "apt", "apt-get", "yum", "dnf", "pacman", "systemctl",
            "journalctl", "ufw", "iptables", "chmod", "chown", "/dev/",
            "/etc/", "/var/", "/usr/", "/home/"
        ]):
            return "linux"

        return "generic"

    def split_chained_commands(self, command: str) -> List[str]:
        """
        Splits chained commands (;, &&, ||, |, &) while respecting quoted strings.
        """
        # Split on operator characters that are not inside quotes
        chunks = []
        current = []
        in_single_quote = False
        in_double_quote = False
        i = 0
        n = len(command)

        while i < n:
            char = command[i]

            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                current.append(char)
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                current.append(char)
            elif not in_single_quote and not in_double_quote:
                # Check for two-character operators: && or ||
                if i + 1 < n and command[i:i+2] in ("&&", "||"):
                    part = "".join(current).strip()
                    if part:
                        chunks.append(part)
                    current = []
                    i += 2
                    continue
                # Single character operators: ; or | or &
                elif char in (";", "|", "&"):
                    part = "".join(current).strip()
                    if part:
                        chunks.append(part)
                    current = []
                    i += 1
                    continue
                else:
                    current.append(char)
            else:
                current.append(char)
            i += 1

        remainder = "".join(current).strip()
        if remainder:
            chunks.append(remainder)

        return chunks if chunks else [command.strip()]

    def normalize_whitespace(self, text: str) -> str:
        """
        Replaces redundant whitespace and tabs with single spaces while preserving quotes.
        """
        return " ".join(text.split())

    def analyze(self, raw_command: str) -> Dict[str, Any]:
        """
        Performs full static security analysis on the raw command string.
        Returns a structured dictionary detailing risks, rule matches, and safe advice.
        """
        if not raw_command or not raw_command.strip():
            return {
                "command": "",
                "risk_level": "SAFE",
                "platform": "generic",
                "findings": ["No command was submitted."],
                "dangerous_patterns": [],
                "explanation": "The prompt was empty.",
                "recommendation": "Enter a valid terminal command or question for analysis.",
                "is_safe": True,
                "requires_review": False,
                "chained_commands": []
            }

        command = raw_command.strip()
        normalized_command = self.normalize_whitespace(command)
        platform = self.detect_platform(command)
        chained_subcommands = self.split_chained_commands(command)

        findings: List[str] = []
        dangerous_patterns: List[str] = []
        explanations: List[str] = []
        recommendations: List[str] = []
        highest_risk = "SAFE"

        def update_risk(new_risk: str):
            nonlocal highest_risk
            if self.RISK_HIERARCHY.get(new_risk, 0) > self.RISK_HIERARCHY.get(highest_risk, 0):
                highest_risk = new_risk

        # 1. Check for command obfuscation and decoding tricks
        for pattern_re, desc in self.compiled_obfuscation:
            if pattern_re.search(command):
                findings.append(desc)
                dangerous_patterns.append(pattern_re.pattern)
                explanations.append("Obfuscation techniques obscure actual system behavior, preventing clear auditing.")
                recommendations.append("De-obfuscate the command and inspect the plaintext instructions before running.")
                update_risk("HIGH")

        # 2. Check full command and each chained component against compiled rules
        targets_to_check = [command, normalized_command] + chained_subcommands

        matched_rule_ids = set()
        for target in targets_to_check:
            for rule in self.compiled_rules:
                if rule["id"] in matched_rule_ids:
                    continue

                # Check if any pattern in the rule matches
                for compiled_pat in rule["compiled_patterns"]:
                    if compiled_pat.search(target):
                        matched_rule_ids.add(rule["id"])
                        findings.append(rule["finding"])
                        dangerous_patterns.append(rule["id"])
                        explanations.append(rule["explanation"])
                        recommendations.append(rule["recommendation"])
                        update_risk(rule["risk_level"])
                        break

        # 3. Check for unbalanced quotes or suspicious nested backticks / subshells
        quote_issues = False
        if command.count('"') % 2 != 0 or command.count("'") % 2 != 0:
            quote_issues = True
            findings.append("Unbalanced quotation marks detected.")
            explanations.append("Unclosed quotes can cause the shell to consume subsequent lines or fail unpredictably.")
            recommendations.append("Ensure all single and double quotation marks are properly closed.")
            update_risk("REVIEW REQUIRED")

        # Backtick execution or command substitution ($(...))
        if re.search(r"`[^`]+`|\$\([^\)]+\)", command):
            findings.append("Command substitution subshell detected (`...` or $(...)).")
            explanations.append("Command substitution evaluates embedded commands dynamically before passing results to the outer command.")
            recommendations.append("Verify the nested command independently to ensure it behaves safely.")
            if highest_risk == "SAFE":
                update_risk("MEDIUM")

        # 4. If no dangerous rules matched, evaluate benign commands vs unknown input
        if highest_risk == "SAFE":
            first_word = command.split()[0].lower() if command.split() else ""
            # Strip path prefix if any (e.g. /usr/bin/ls -> ls)
            base_cmd = first_word.split("/")[-1].split("\\")[-1]

            if base_cmd in self.BENIGN_COMMANDS:
                findings.append(f"Standard operational command ('{base_cmd}') with no destructive parameters detected.")
                explanations.append(f"'{base_cmd}' is a commonly used utility that performs standard system querying or safe program execution.")
                recommendations.append("This command is typical for everyday workflow. Run when needed.")
            elif len(command) > 0:
                # Unfamiliar command without known rule match -> REVIEW REQUIRED
                update_risk("REVIEW REQUIRED")
                findings.append(f"Unfamiliar command or custom script ('{base_cmd}'). No known destructive rules triggered, but behavior cannot be verified deterministically.")
                explanations.append("The command is not recognized as a standard built-in or known safe utility. Its effects depend on custom binaries or system state.")
                recommendations.append("Check the tool's documentation or run with '--help' to inspect parameters before executing.")

        # Consolidate explanation and recommendation
        primary_explanation = " ".join(explanations) if explanations else "The command appears harmless based on deterministic rule analysis."
        primary_recommendation = " ".join(recommendations) if recommendations else "Review parameters if operating on production environments."

        is_safe = (highest_risk == "SAFE")
        requires_review = (highest_risk in ("REVIEW REQUIRED", "HIGH", "CRITICAL"))

        return {
            "command": raw_command,
            "risk_level": highest_risk,
            "platform": platform,
            "findings": findings,
            "dangerous_patterns": dangerous_patterns,
            "explanation": primary_explanation,
            "recommendation": primary_recommendation,
            "is_safe": is_safe,
            "requires_review": requires_review,
            "chained_commands": chained_subcommands if len(chained_subcommands) > 1 else []
        }
