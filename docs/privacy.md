# Privacy Architecture & Security Guarantees 🔒

Privacy is a non-negotiable architectural pillar of **GhostShell: The Haunted AI Terminal**. Unlike standard AI assistants that route user prompts, environment tokens, and shell commands to third-party commercial cloud APIs, GhostShell is engineered from the ground up for strict local isolation.

---

## 1. Core Privacy Commitments

| Guarantee | Implementation | Verification |
| :--- | :--- | :--- |
| **Strict Loopback Binding** | Flask dev server binds exclusively to `127.0.0.1` | Cannot be queried from other devices on the LAN |
| **Zero Cloud AI Egress** | Inference queries Ollama locally at `http://127.0.0.1:11434` | Zero outbound API keys or requests to OpenAI/Anthropic/Google |
| **No Disk Logging of Prompts** | Prompts and analysis requests are held in volatile process RAM | No SQLite, file logs, or history persisted to disk |
| **Zero Telemetry / Analytics** | No Google Analytics, Sentry, Mixpanel, or pingbacks | Completely free of tracking scripts or cookies |
| **Simulated Execution Boundary** | Commands are parsed as string tokens | `eval()`, `exec()`, `shell=True` are strictly prohibited |
| **SSRF Defense** | Validates base URL against loopback hosts (`127.0.0.1`, `localhost`) | Blocks requests to intranet metadata or internal IP ranges |

---

## 2. Why Open-Weight Local AI is Essential for Shell Auditing

Terminal commands frequently touch confidential developer assets:
- Environment variables (`AWS_SECRET_ACCESS_KEY`, `DATABASE_URL`)
- File paths containing usernames or proprietary project codenames
- Private SSH keys (`~/.ssh/id_rsa`)
- Deployment credentials and API tokens

Sending these command strings to external cloud AI vendors introduces immediate data-leakage and compliance violations (e.g., GDPR, SOC2, HIPAA). GhostShell ensures that your command auditing remains confidential on your developer machine.

---

## 3. How to Verify GhostShell's Offline Operation

To verify that GhostShell makes no external network calls during normal operation:

1. **Disconnect Network / Enable Airplane Mode:**
   Turn off Wi-Fi or disconnect your ethernet cable.
2. **Start GhostShell & Ollama:**
   ```powershell
   # In terminal 1:
   ollama run qwen2.5:3b

   # In terminal 2:
   python app.py
   ```
3. **Audit Commands & Chat:**
   Open `http://127.0.0.1:5000` in your browser. All safety analysis, chat explanations, and Haunted Archives story generation will function with zero internet connectivity.
4. **Inspect Traffic with Wireshark or Fiddler:**
   Monitor outgoing packets. You will see HTTP traffic solely on `127.0.0.1:5000` and `127.0.0.1:11434`.

---

## 4. Threat Model & Realistic Limitations

> [!WARNING]
> While GhostShell protects your prompts from cloud transmission, local security still relies on the integrity of your host operating system.

- **Host Machine Compromise:** If an attacker already has root/administrator access or malware installed on your workstation, they could inspect memory or local files.
- **Model Download Integrity:** Initial model pulls (`ollama pull <model>`) require an internet connection to download weights from Ollama's registry. Always verify model provenance.
- **Advisory Nature of Static Analysis:** The deterministic command analyzer is a safety heuristic and training tool. It cannot foresee all runtime edge cases or bespoke binaries.
