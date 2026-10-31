"""
GhostShell: The Haunted AI Terminal.
Flask web server powering the local, open-source AI terminal experience.
"""

import os
import logging
from flask import (
    Flask, render_template, request, jsonify, Response, stream_with_context, send_from_directory
)
from werkzeug.exceptions import RequestEntityTooLarge
from config import Config
from ghostshell.command_analyzer import CommandSafetyAnalyzer
from ghostshell.ai_engine import OllamaAIEngine
from ghostshell.validators import (
    validate_command_input,
    validate_chat_input,
    validate_story_params,
    validate_model_name
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ghostshell")

def create_app(config_class=Config):
    """Application factory for GhostShell."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize deterministic safety analyzer and local AI engine
    analyzer = CommandSafetyAnalyzer()
    ai_engine = OllamaAIEngine(
        base_url=app.config.get("OLLAMA_BASE_URL"),
        model=app.config.get("OLLAMA_MODEL"),
        timeout=app.config.get("OLLAMA_TIMEOUT_SECONDS")
    )

    # Security Headers middleware
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "img-src 'self' data:; "
            "font-src 'self' data:;"
        )
        return response

    # Error Handlers
    @app.errorhandler(RequestEntityTooLarge)
    def handle_payload_too_large(e):
        return jsonify({
            "error": "Spectral payload too large. Request body exceeds safety limit (64 KB).",
            "code": "PAYLOAD_TOO_LARGE"
        }), 413

    @app.errorhandler(404)
    def handle_not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Spectral endpoint not found in the machine.", "code": "NOT_FOUND"}), 404
        return render_template("index.html"), 404

    @app.errorhandler(500)
    def handle_server_error(e):
        logger.error(f"Internal server error: {e}")
        return jsonify({
            "error": "A phantom glitch disturbed the server. Check logs for details.",
            "code": "INTERNAL_ERROR"
        }), 500

    # Web Routes
    @app.route("/css/<path:filename>")
    def serve_css(filename):
        """Serves CSS files directly from static/css or css/."""
        return send_from_directory(os.path.join(app.root_path, "static", "css"), filename)

    @app.route("/")
    def index():
        """Main haunted terminal interface."""
        status = ai_engine.check_status()
        return render_template("index.html", status=status, config=app.config)

    @app.route("/settings")
    def settings_view():
        """Settings page for local model configuration and privacy verification."""
        status = ai_engine.check_status()
        return render_template("settings.html", status=status, config=app.config)

    # API Routes
    @app.route("/api/status", methods=["GET"])
    def get_status():
        """Returns the local AI runtime status, available models, and current configuration."""
        status = ai_engine.check_status()
        return jsonify({
            "status": "online" if status["available"] else "offline",
            "ollama_available": status["available"],
            "base_url": status["base_url"],
            "current_model": status["current_model"],
            "model_available": status["model_available"],
            "installed_models": status["installed_models"],
            "error": status["error"],
            "setup_guide": status["setup_guide"]
        })

    @app.route("/api/models", methods=["GET"])
    def list_models():
        """Returns compatible locally installed models found in Ollama."""
        status = ai_engine.check_status()
        return jsonify({
            "available": status["available"],
            "models": status["installed_models"],
            "current_model": status["current_model"]
        })

    @app.route("/api/settings/model", methods=["POST"])
    def switch_model():
        """Changes the selected local model after validating input."""
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid request body. Expected JSON object.", "code": "INVALID_JSON"}), 400

        model_name = data.get("model")
        is_valid, sanitized_name, err = validate_model_name(model_name)
        if not is_valid:
            return jsonify({"error": err, "code": "VALIDATION_ERROR"}), 400

        # Update active model in memory
        status = ai_engine.set_model(sanitized_name)
        return jsonify({
            "message": f"GhostShell switched to model '{sanitized_name}'.",
            "current_model": status["current_model"],
            "model_available": status["model_available"],
            "error": status["error"],
            "setup_guide": status["setup_guide"]
        })

    @app.route("/api/chat", methods=["POST"])
    def chat():
        """Processes a conversational user message with the Ghost."""
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid JSON body provided.", "code": "INVALID_JSON"}), 400

        message = data.get("message")
        history = data.get("history", [])
        stream = data.get("stream", False)

        is_valid, clean_msg, err = validate_chat_input(message)
        if not is_valid:
            return jsonify({"error": err, "code": "VALIDATION_ERROR"}), 400

        from ghostshell.prompts import build_chat_prompt
        messages = build_chat_prompt(clean_msg, history)

        if stream:
            def generate():
                for chunk in ai_engine.generate_chat_stream(messages):
                    yield f"data: {chunk.strip()}\n\n"
            return Response(stream_with_context(generate()), mimetype="text/event-stream")
        else:
            result = ai_engine.generate_chat_sync(messages)
            return jsonify(result)

    @app.route("/api/analyze-command", methods=["POST"])
    def analyze_command():
        """
        Analyzes a submitted shell command using deterministic rules.
        Optionally generates an AI explanation using the local open-weight model.
        The deterministic risk classification is ALWAYS preserved.
        """
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid JSON payload.", "code": "INVALID_JSON"}), 400

        command = data.get("command")
        with_ai = data.get("with_ai", True)
        stream_ai = data.get("stream", False)

        is_valid, clean_cmd, err = validate_command_input(command)
        if not is_valid:
            return jsonify({"error": err, "code": "VALIDATION_ERROR"}), 400

        # 1. Deterministic Security Analysis (NEVER executes the command)
        analysis_result = analyzer.analyze(clean_cmd)

        # 2. If AI explanation is requested, query the local model
        if with_ai:
            ai_status = ai_engine.check_status()
            if not ai_status["available"] or not ai_status["model_available"]:
                # When AI is offline, return the deterministic findings with an explicit note
                analysis_result["ai_explanation"] = (
                    "👻 *The Ghost's neural voice is dormant (Ollama is offline or model is missing).*\n\n"
                    "Deterministic analysis is complete and shown above. "
                    "To enable AI explanations, start Ollama and run `ollama run qwen2.5:3b`."
                )
                analysis_result["ai_available"] = False
                return jsonify(analysis_result)

            if stream_ai:
                from ghostshell.prompts import build_command_explanation_prompt
                messages = build_command_explanation_prompt(clean_cmd, analysis_result)

                def generate():
                    # First send initial deterministic metadata
                    import json
                    yield f"data: {json.dumps({'type': 'analysis', 'data': analysis_result})}\n\n"
                    for chunk in ai_engine.generate_chat_stream(messages):
                        yield f"data: {chunk.strip()}\n\n"
                return Response(stream_with_context(generate()), mimetype="text/event-stream")
            else:
                ai_resp = ai_engine.explain_command(clean_cmd, analysis_result, stream=False)
                analysis_result["ai_explanation"] = ai_resp.get("content", "")
                analysis_result["ai_available"] = ai_resp.get("success", False)
                return jsonify(analysis_result)

        return jsonify(analysis_result)

    @app.route("/api/story", methods=["POST"])
    def generate_story():
        """Generates a fictional horror story or incident report via Haunted Archives."""
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid request body.", "code": "INVALID_JSON"}), 400

        is_valid, params, err = validate_story_params(data)
        if not is_valid:
            return jsonify({"error": err, "code": "VALIDATION_ERROR"}), 400

        stream = data.get("stream", False)
        status = ai_engine.check_status()

        if not status["available"]:
            # Provide an offline sample archive log so the feature is demonstrable even before Ollama starts
            sample_story = (
                "```text\n"
                "[HAUNTED ARCHIVES // INCIDENT REPORT #0x33A-NULL]\n"
                "Timestamp: 1997-11-13 03:33:01 UTC\n"
                "System: Subterranean Mainframe Unit 7\n"
                "Severity: SPECTRAL ANOMALY\n\n"
                "[03:33:01] kernel: phantom interrupt on IRQ 0xDEAD.\n"
                "[03:33:04] auth: Session opened for user 'nobody' on ttyS0.\n"
                "[03:33:09] storage: Reading sector 0... byte stream repeating: 'LET ME OUT'.\n"
                "[03:33:14] sysadmin: Attempted kill -9 on PID 666. Return code: PERMISSION DENIED BY ENTITY.\n"
                "```\n\n"
                "👻 *Notice: Local AI runtime (Ollama) is currently offline.*\n"
                "GhostShell rendered a pre-archived anomaly log above. "
                "Awaken Ollama (`ollama run qwen2.5:3b`) to generate infinite real-time horror stories!"
            )
            return jsonify({
                "success": False,
                "story": sample_story,
                "offline": True,
                "error": status["error"]
            })

        if stream:
            from ghostshell.prompts import build_story_prompt
            messages = build_story_prompt(params)
            def generate():
                for chunk in ai_engine.generate_story(params, stream=True):
                    yield f"data: {chunk.strip()}\n\n"
            return Response(stream_with_context(generate()), mimetype="text/event-stream")
        else:
            result = ai_engine.generate_story(params, stream=False)
            return jsonify({
                "success": result.get("success", False),
                "story": result.get("content", ""),
                "model": result.get("model", "")
            })

    return app


app = create_app()

if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # strictly bind to local loopback 127.0.0.1 for privacy
    host = Config.HOST
    port = Config.PORT
    debug = Config.DEBUG
    print(f"[GhostShell] The Haunted AI Terminal starting on http://{host}:{port}")
    print("[Safety] Commands are analyzed deterministically as text and are NEVER executed.")
    app.run(host=host, port=port, debug=debug)
