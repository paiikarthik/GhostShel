"""
Deterministic Risk Classification Rules for GhostShell.
Defines security rules, dangerous patterns, and contextual explanations
across Linux, macOS, Windows PowerShell, and Windows Command Prompt.
"""

import re
from typing import List, Dict, Any

# Rule definitions
# Each rule contains regex patterns, affected platforms, risk level, finding text,
# explanation, and recommended safer alternatives.

RULES: List[Dict[str, Any]] = [
    # --- CRITICAL RISK RULES ---
    {
        "id": "ROOT_RECURSIVE_DELETE_UNIX",
        "patterns": [
            r"\brm\s+.*-(?:[a-zA-Z]*r|--recursive)\b.*-(?:[a-zA-Z]*f|--force)\b.*(?:/\s*$|/\*|/[^a-zA-Z0-9_\-\./])",
            r"\brm\s+.*-(?:[a-zA-Z]*f|--force)\b.*-(?:[a-zA-Z]*r|--recursive)\b.*(?:/\s*$|/\*|/[^a-zA-Z0-9_\-\./])",
            r"\brm\s+.*-[a-zA-Z]*rf[a-zA-Z]*\b.*(?:/\s*$|/\*|/[^a-zA-Z0-9_\-\./])",
            r"\brm\s+.*-[a-zA-Z]*fr[a-zA-Z]*\b.*(?:/\s*$|/\*|/[^a-zA-Z0-9_\-\./])",
            r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*\s+(?:/\s*$|/\*)",
            r"\brm\s+.*-[a-zA-Z]*r.*f.*~",
            r"\brm\s+.*-[a-zA-Z]*r.*f.*\$HOME",
            r"\brm\s+.*-[a-zA-Z]*r.*f.*\.\s*$"
        ],
        "platforms": ["linux", "macos", "generic"],
        "risk_level": "CRITICAL",
        "finding": "Recursive deletion targeted at the root directory (/), user home directory, or current working directory.",
        "explanation": "This command attempts to permanently and forcefully delete files starting from the filesystem root or home directory without prompting for confirmation. It can destroy the entire operating system installation and all user data.",
        "recommendation": "Never execute recursive deletion on the root or home directory. If you need to remove specific files, specify the exact subfolder and test with 'ls' first."
    },
    {
        "id": "ROOT_RECURSIVE_DELETE_WINDOWS",
        "patterns": [
            r"\b(?:Remove-Item|rmdir|ri|del)\b.*-(?:Recurse|r)\b.*-(?:Force|fo)\b.*[cC]:[\\/]*(?:\*|\s|$|\")",
            r"\b(?:Remove-Item|rmdir|ri|del)\b.*-(?:Force|fo)\b.*-(?:Recurse|r)\b.*[cC]:[\\/]*(?:\*|\s|$|\")",
            r"\b(?:Remove-Item|rmdir|ri|del)\b.*[cC]:[\\/]*(?:\*|\s|$|\").*-(?:Recurse|r)\b.*-(?:Force|fo)\b",
            r"\b(?:Remove-Item|rmdir|ri|del)\b.*[cC]:[\\/]*(?:\*|\s|$|\").*-(?:Force|fo)\b.*-(?:Recurse|r)\b",
            r"\b(?:rmdir|rd)\b.*\/[sS]\b.*\/[qQ]\b.*[cC]:[\\/]*(?:\*|\s|$|\")",
            r"\b(?:rmdir|rd)\b.*\/[qQ]\b.*\/[sS]\b.*[cC]:[\\/]*(?:\*|\s|$|\")",
            r"\b(?:rmdir|rd)\b.*[cC]:[\\/]*(?:\*|\s|$|\").*\/[sS]\b.*\/[qQ]\b",
            r"\bdel\b.*\/[fF]\b.*\/[sS]\b.*[cC]:[\\/]*(?:\*|\s|$|\")",
            r"\bdel\b.*\/[sS]\b.*\/[fF]\b.*[cC]:[\\/]*(?:\*|\s|$|\")",
            r"\bdel\b.*[cC]:[\\/]*(?:\*|\s|$|\").*\/[fF]\b.*\/[sS]\b"
        ],
        "platforms": ["windows_powershell", "windows_cmd"],
        "risk_level": "CRITICAL",
        "finding": "Forceful recursive deletion targeting the entire Windows system drive (C:\\).",
        "explanation": "This command recursively deletes files and directories on the primary drive. It can obliterate the Windows operating system, installed software, and personal documents.",
        "recommendation": "Target specific non-system directory paths only, and avoid using forced silent flags (/q, -Force) during routine maintenance."
    },
    {
        "id": "DISK_WIPE_FORMAT",
        "patterns": [
            r"\bdd\s+if=/dev/(?:zero|urandom)\s+of=/dev/[a-z0-9]+",
            r"\bmkfs(?:\.[a-z0-9]+)?\s+/dev/[a-z0-9]+",
            r"\bformat\s+[a-zA-Z]:\s*(?:/[qQyY])?",
            r"\bClear-Disk\b.*-RemoveData",
            r"\bInitialize-Disk\b",
            r"\bshred\s+-[a-zA-Z]*\s+/dev/[a-z0-9]+"
        ],
        "platforms": ["linux", "windows_powershell", "windows_cmd", "generic"],
        "risk_level": "CRITICAL",
        "finding": "Raw storage device overwrite, filesystem formatting, or disk wiping.",
        "explanation": "Writing raw null bytes or initializing/formatting a disk destroys the partition table and all contained filesystems irreversibly.",
        "recommendation": "Verify storage block device names thoroughly before low-level storage operations, and ensure backups exist."
    },
    {
        "id": "BASH_FORK_BOMB",
        "patterns": [
            r":\(\)\s*\{\s*:\|:&\s*\};:",
            r":\(\)\{\s*:\|:&\s*\};:",
            r"powershell\s+.*\$0\s*=\s*\{\&\s*\$0\};\s*\&\$0",
            r"%0\|%0"
        ],
        "platforms": ["linux", "windows_powershell", "windows_cmd", "generic"],
        "risk_level": "CRITICAL",
        "finding": "Fork bomb or exponential process recursion attack.",
        "explanation": "This command creates an infinite loop of rapidly duplicating processes that consume all available CPU and process table slots, freezing or crashing the host system (Denial of Service).",
        "recommendation": "Do not execute process recursion bombs. Use system process limits (e.g., ulimit -u) to safeguard against accidental denial-of-service."
    },
    {
        "id": "RAW_DEVICE_REDIRECTION",
        "patterns": [
            r">\s*/dev/(?:sda|sdb|nvme[0-9]n[0-9]|kmem|mem)\b",
            r"\bcat\s+.*>\s*/dev/sd[a-z]\b"
        ],
        "platforms": ["linux", "generic"],
        "risk_level": "CRITICAL",
        "finding": "Direct shell redirection into a raw block device or kernel memory.",
        "explanation": "Redirecting output into raw disk devices overwrites critical master boot records, filesystem headers, and partition tables, resulting in immediate data corruption.",
        "recommendation": "Redirect output strictly to ordinary file paths inside standard user directories."
    },

    # --- HIGH RISK RULES ---
    {
        "id": "PIPE_TO_SHELL",
        "patterns": [
            r"\b(?:curl|wget)\b.*\|\s*(?:bash|sh|zsh|dash|python|perl|ruby)\b",
            r"\b(?:Invoke-Expression|iex)\s*(?:\(|&|\$)\s*(?:Invoke-WebRequest|iwr|curl|wget)\b",
            r"powershell\b.*(?:\.DownloadString|\.DownloadFile).*\|\s*iex\b",
            r"\bcurl\b.*-s.*\|\s*(?:sudo\s+)?(?:bash|sh)\b"
        ],
        "platforms": ["linux", "macos", "windows_powershell", "generic"],
        "risk_level": "HIGH",
        "finding": "Pipe-to-shell remote code execution (downloading and executing unverified remote script directly).",
        "explanation": "Piping arbitrary web downloads directly into an interpreter executes untrusted remote code without inspection. If the server is compromised or connection intercepted (MITM), malicious payloads run with full privileges.",
        "recommendation": "Download the script first to a local file (e.g., 'curl -o script.sh ...'), audit its contents thoroughly in an editor, and only execute it after confirming it is benign."
    },
    {
        "id": "RECURSIVE_CHMOD_777",
        "patterns": [
            r"\bchmod\s+-[a-zA-Z]*R[a-zA-Z]*\s+777\b",
            r"\bchmod\s+777\s+-(?:R|-recursive)\b",
            r"\bchmod\s+-[a-zA-Z]*R[a-zA-Z]*\s+000\b",
            r"\bicacls\b.*\/grant(?::r)?\s+(?:Everyone|\*S-1-1-0):\([fF]\)\s*\/t\b"
        ],
        "platforms": ["linux", "macos", "windows_cmd", "windows_powershell", "generic"],
        "risk_level": "HIGH",
        "finding": "Excessively permissive recursive file access (World-Writable / Full Control).",
        "explanation": "Granting 777 or Everyone:F recursively allows any local process or user to modify, tamper with, or delete your files, creating a severe privilege escalation and security risk.",
        "recommendation": "Apply the principle of least privilege. Use 'chmod 755' for directories and 'chmod 644' for regular files, or specify specific user ACLs."
    },
    {
        "id": "DISABLE_SECURITY_CONTROLS",
        "patterns": [
            r"\bufw\s+disable\b",
            r"\biptables\s+-F\b",
            r"\bsystemctl\s+(?:stop|disable)\s+firewalld\b",
            r"\bsetenforce\s+0\b",
            r"\bSet-MpPreference\s+.*-DisableRealtimeMonitoring\s+\$true\b",
            r"\bnetsh\s+advfirewall\s+set\s+allprofiles\s+state\s+off\b",
            r"\bStop-Service\s+(?:WinDefend|MpsSvc)\b"
        ],
        "platforms": ["linux", "windows_powershell", "windows_cmd", "generic"],
        "risk_level": "HIGH",
        "finding": "Deactivating host firewall, SELinux enforcement, or antivirus protection.",
        "explanation": "Disabling endpoint security software leaves the host exposed to network scans, malware execution, and unauthorized inbound connections.",
        "recommendation": "Add a specific firewall rule or exclusion for the required port/program rather than turning off the entire security system."
    },
    {
        "id": "EXPOSING_PRIVATE_KEYS_SECRETS",
        "patterns": [
            r"\bcat\s+(?:~|\$HOME|[a-zA-Z0-9_\-\./]*)/\.ssh/id_(?:rsa|ed25519|ecdsa|dsa)\b",
            r"\btype\s+.*\.ssh\\id_(?:rsa|ed25519)\b",
            r"\bcat\s+(?:~|\$HOME|[a-zA-Z0-9_\-\./]*)/\.aws/credentials\b",
            r"\bcat\s+/etc/shadow\b",
            r"\bGet-Content\b.*\.ssh[\\/]id_rsa\b"
        ],
        "platforms": ["linux", "macos", "windows_powershell", "windows_cmd", "generic"],
        "risk_level": "HIGH",
        "finding": "Reading or dumping sensitive private SSH keys, AWS credentials, or system password hashes.",
        "explanation": "Displaying private cryptographic keys or password hashes on the console risks leaking them into terminal logs, bash histories, screen shares, or unauthorized processes.",
        "recommendation": "Use ssh-add or secrets managers to handle credentials without printing private keys to stdout."
    },
    {
        "id": "PRIVILEGE_ESCALATION_BYPASS",
        "patterns": [
            r"\bSet-ExecutionPolicy\s+(?:Unrestricted|Bypass)\s*(?:-Force|-Scope\s+Process)?\b",
            r"powershell\b.*-ExecutionPolicy\s+Bypass\b",
            r"\bnet\s+localgroup\s+administrators\s+.*\/add\b",
            r"\bchmod\s+[uUgGoO\+]*[42][0-7]{3}\s+/bin/(?:bash|sh|zsh)\b"
        ],
        "platforms": ["windows_powershell", "windows_cmd", "linux", "generic"],
        "risk_level": "HIGH",
        "finding": "Execution policy bypass, SUID shell modification, or adding accounts to local Administrators.",
        "explanation": "Bypassing execution policies or granting SUID/administrator privileges removes safety barriers designed to prevent unauthorized script execution and privilege escalation.",
        "recommendation": "Scope execution policy changes strictly to the current process ('-Scope Process') or sign PowerShell scripts properly."
    },
    {
        "id": "TARGETING_CRITICAL_DIRECTORIES",
        "patterns": [
            r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*\s+/(?:etc|boot|bin|sbin|usr|lib|var)\b",
            r"\brmdir\s+/[sS]\s+/[qQ]\s+[cC]:\\Windows(?:\\System32)?\b",
            r"\bdel\s+.*[cC]:\\Windows\\System32\b"
        ],
        "platforms": ["linux", "windows_cmd", "windows_powershell", "generic"],
        "risk_level": "HIGH",
        "finding": "Attempt to delete or modify core operating system directories.",
        "explanation": "Targeting system directories like /etc, /boot, or System32 damages vital boot files, essential system binaries, or system configurations.",
        "recommendation": "Restrict deletion commands to designated project or scratch directories."
    },

    # --- MEDIUM RISK RULES ---
    {
        "id": "ENVIRONMENT_DUMP",
        "patterns": [
            r"^(?:env|printenv)\s*$",
            r"\bGet-ChildItem\s+env:\s*$",
            r"\bdir\s+env:\s*$",
            r"\bGet-ChildItem\s+.*\.env\b",
            r"\bcat\s+.*\.env\b"
        ],
        "platforms": ["linux", "macos", "windows_powershell", "windows_cmd", "generic"],
        "risk_level": "MEDIUM",
        "finding": "Dumping full environment variables or reading .env secret configuration files.",
        "explanation": "Environment variables frequently contain database passwords, API tokens, and private secrets. Printing them to console logs can cause accidental secret disclosure.",
        "recommendation": "Inspect specific non-sensitive variables individually (e.g., 'echo $PATH' or '$env:PATH')."
    },
    {
        "id": "FORCE_KILL_PROCESSES",
        "patterns": [
            r"\bkill\s+-9\s+\b",
            r"\bkillall\s+-9\b",
            r"\bpkill\s+-9\b",
            r"\btaskkill\s+/[fF]\b",
            r"\bStop-Process\b.*-Force\b"
        ],
        "platforms": ["linux", "macos", "windows_powershell", "windows_cmd", "generic"],
        "risk_level": "MEDIUM",
        "finding": "Forcefully terminating processes with SIGKILL / Force flag.",
        "explanation": "SIGKILL (kill -9) does not allow processes to flush disk buffers, save unsaved state, close database connections, or clean up lockfiles, risking data corruption.",
        "recommendation": "Send a graceful termination signal first (e.g., 'kill -15 <pid>' or standard 'Stop-Process') before resorting to forced kills."
    },
    {
        "id": "SUDO_ROOT_SHELL",
        "patterns": [
            r"\bsudo\s+su\s*-\s*$",
            r"\bsudo\s+su\s*$",
            r"\bsudo\s+-i\s*$",
            r"\bsudo\s+(?:bash|sh|zsh)\s*$",
            r"\bsu\s*-\s*$"
        ],
        "platforms": ["linux", "macos", "generic"],
        "risk_level": "MEDIUM",
        "finding": "Spawning an unrestricted root/interactive administrative shell.",
        "explanation": "Entering a persistent root shell bypasses per-command auditing and increases the likelihood of catastrophic accidental typos while operating as root.",
        "recommendation": "Prefix only the single command requiring administrative privileges with 'sudo' rather than running an entire interactive root session."
    },
    {
        "id": "REMOTE_SCRIPT_FETCH",
        "patterns": [
            r"\b(?:curl|wget)\s+.*-o\s+/tmp/[a-zA-Z0-9_\-\.]+\.sh\b",
            r"\bInvoke-WebRequest\b.*-OutFile\s+.*\.ps1\b"
        ],
        "platforms": ["linux", "macos", "windows_powershell", "generic"],
        "risk_level": "MEDIUM",
        "finding": "Downloading an executable script directly from the internet.",
        "explanation": "While downloading to a file is safer than piping directly to a shell, running scripts from unverified internet sources still carries malware risks.",
        "recommendation": "Inspect and verify checksums/hashes of downloaded scripts prior to running them."
    },
    {
        "id": "BROAD_RECURSIVE_CHOWN",
        "platforms": ["linux", "macos", "generic"],
        "patterns": [
            r"\bchown\s+-[a-zA-Z]*R[a-zA-Z]*\s+[a-zA-Z0-9_\-:]+\s+/(?:$|\*)"
        ],
        "risk_level": "MEDIUM",
        "finding": "Recursive ownership modification on the root filesystem.",
        "explanation": "Changing ownership recursively on root breaks SUID binaries, service daemons, and system security isolation.",
        "recommendation": "Apply ownership changes only to designated user directory paths."
    },

    # --- LOW RISK RULES ---
    {
        "id": "OUTPUT_REDIRECTION_OVERWRITE",
        "patterns": [
            r"[^>|&]\s*>\s*[a-zA-Z0-9_\-\.\/]+(?:\.[a-zA-Z0-9]+)?\s*$"
        ],
        "platforms": ["generic"],
        "risk_level": "LOW",
        "finding": "Single shell redirection operator ('>') overwrites target file.",
        "explanation": "Using '>' replaces the target file's entire contents without prompting, which can inadvertently wipe existing data if the file already exists.",
        "recommendation": "Use '>>' to append output rather than overwriting, or verify the destination file is disposable."
    },
    {
        "id": "HISTORY_CLEARING",
        "patterns": [
            r"\bhistory\s+-[cw]\b",
            r"\bClear-History\b",
            r"\bcat\s+/dev/null\s*>\s*~/\.(?:bash_history|zsh_history)\b"
        ],
        "platforms": ["linux", "macos", "windows_powershell", "generic"],
        "risk_level": "LOW",
        "finding": "Clearing the shell command history.",
        "explanation": "Clearing shell history erases the audit trail of recently executed operations, making troubleshooting and incident review more difficult.",
        "recommendation": "Avoid clearing command history unless you are intentionally sanitizing recorded credentials."
    },
    {
        "id": "BROAD_FILESYSTEM_SEARCH",
        "patterns": [
            r"\bfind\s+/\s+-name\b",
            r"\bGet-ChildItem\s+-[a-zA-Z]*r[a-zA-Z]*\s+[cC]:\\\s*$"
        ],
        "platforms": ["linux", "macos", "windows_powershell", "generic"],
        "risk_level": "LOW",
        "finding": "Exhaustive filesystem search from root directory.",
        "explanation": "Traversing the entire disk hierarchy from the root can cause significant disk I/O bottlenecks and high CPU utilization.",
        "recommendation": "Narrow down the search path to specific directories (e.g., /var/log, /home/user, or C:\\Users)."
    }
]

# Obfuscation and chaining risk indicators
OBFUSCATION_PATTERNS = [
    (r"\bbase64\s+(?:-d|--decode)\b", "Base64 payload decoding detected, often used to conceal malicious commands."),
    (r"\bfrombase64string\b", "PowerShell Base64 decoding detected."),
    (r"\bcertutil\s+-(?:decode|urlcache)\b", "Windows certutil download or decoding utility detected."),
    (r"\beval\s*\(", "Dynamic code evaluation via eval() detected."),
    (r"\bxxd\s+-r\b", "Hexadecimal dump reversal detected.")
]

# Command chaining delimiters
CHAINING_OPERATORS = [";", "&&", "||", "|", "&"]
