from flask import Blueprint, request, jsonify, current_app
import requests
from config import Config
from .agent import run_agent
from . import tools as tools_impl

rag_bp = Blueprint("rag", __name__)

@rag_bp.route("/ask", methods=["GET"])
def ask_get():
    return jsonify({"ok": True, "hint": "Use POST with JSON {message, sessionId} and x-api-key header"}), 200

@rag_bp.route("/ask", methods=["POST"])
def ask_post():
    try:
        if request.headers.get("x-api-key") != Config.X_API_KEY:
            return jsonify({"detail": "Unauthorized"}), 401

        data = request.get_json(force=True) or {}
        message = data.get("message", "")
        session_id = data.get("sessionId", "default")
        if not message:
            return jsonify({"error": "No message provided"}), 400
        if not Config.OPENAI_API_KEY:
            return jsonify({"error": "OPENAI_API_KEY missing"}), 500

        answer = run_agent(session_id=session_id, user_text=message, tools_impl=tools_impl)
        return jsonify({"answer": answer})

    except requests.HTTPError as e:
        txt = getattr(e.response, "text", "") or str(e)
        return jsonify({"error":"openai_http", "status": getattr(e.response, "status_code", None), "detail": txt[:400]}), 502
    except Exception as e:
        current_app.logger.exception("rag /ask failed")
        return jsonify({"error":"internal", "detail": str(e)[:200]}), 500
