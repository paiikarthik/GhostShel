# Supported Local Models & Licensing Guide 🧠

GhostShell relies on open-weight language models served locally via [Ollama](https://ollama.com). This guide explains compatible models, hardware footprints, and licensing distinctions.

---

## 1. Compatible Open-Weight Models

| Model | Parameters | Download Size | RAM / VRAM | License | Best Suited For | Ollama Pull Command |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen 2.5 3B** *(Default)* | 3.09 B | ~1.9 GB | 6–8 GB | Apache 2.0 | Balanced accuracy, witty explanations, code comprehension | `ollama run qwen2.5:3b` |
| **Llama 3.2 1B** | 1.23 B | ~1.3 GB | 4 GB | Llama 3.2 Community | Ultra-lightweight laptops, minimal memory footprint | `ollama run llama3.2:1b` |
| **DeepSeek R1 1.5B** | 1.5 B | ~1.1 GB | 4–6 GB | MIT | Step-by-step reasoning and technical decomposition | `ollama run deepseek-r1:1.5b` |
| **Mistral 7B** | 7.24 B | ~4.1 GB | 12–16 GB | Apache 2.0 | Rich cyber creepypastas, in-depth security insights | `ollama run mistral:7b` |

---

## 2. Open-Source vs. Open-Weight Licensing Notice

> [!IMPORTANT]
> A distinction exists between GhostShell's software license, the open-weight model licenses, and runtime dependencies.

### GhostShell Application Code
- **License:** MIT License.
- **Terms:** Fully open-source, permissive, allows modification, distribution, and private use.

### Model Weights Licensing
- **Qwen 2.5 (3B):** Released under the permissive **Apache 2.0 License** by the Qwen team. Commercial and research use permitted.
- **DeepSeek R1 (1.5B):** Released under the **MIT License**.
- **Mistral 7B:** Released under the **Apache 2.0 License**.
- **Llama 3.2 (1B/3B):** Released under the **Meta Llama 3.2 Community License**. Free for research and commercial use up to 700 million monthly active users; requires adherence to Meta's Acceptable Use Policy.

Users must independently verify model license terms before redistributing weights or deploying models commercially.

---

## 3. Ollama Installation & Setup

### Windows
1. Download the Windows installer from [ollama.com/download/windows](https://ollama.com/download/windows).
2. Run `OllamaSetup.exe`.
3. Open PowerShell or Command Prompt and test the daemon:
   ```powershell
   ollama --version
   ```
4. Pull your desired model:
   ```powershell
   ollama run qwen2.5:3b
   ```

### macOS
1. Download from [ollama.com/download/mac](https://ollama.com/download/mac) or install via Homebrew:
   ```bash
   brew install ollama
   ```
2. Pull and start:
   ```bash
   ollama run qwen2.5:3b
   ```

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama run qwen2.5:3b
```

---

## 4. Switching Models in GhostShell

You can switch models in three ways:
1. **Interactive UI:** Click **Settings (⚙️)** in the top right header, pick from installed models or enter a custom model name, and click **Save Model**.
2. **Environment Variable:** Set `OLLAMA_MODEL=llama3.2:1b` in your `.env` file.
3. **REST API:**
   ```bash
   curl -X POST http://127.0.0.1:5000/api/settings/model \
     -H "Content-Type: application/json" \
     -d '{"model": "llama3.2:1b"}'
   ```
