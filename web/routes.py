from __future__ import annotations
import threading
import uuid
from collections import OrderedDict
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    current_app,
    session,
)
from core import ExpressionEvaluator, MatrixError, format_result

main_bp = Blueprint("main", __name__)
_evaluators: "OrderedDict[str, ExpressionEvaluator]" = OrderedDict()
_evaluators_lock = threading.Lock()
_MAX_SESSIONS = 1000


def _get_session_id() -> str:
    if "sid" not in session:
        session.permanent = True
        session["sid"] = uuid.uuid4().hex
    return session["sid"]

def _get_evaluator() -> ExpressionEvaluator:
    sid = _get_session_id()
    with _evaluators_lock:
        if sid in _evaluators:
            _evaluators.move_to_end(sid)
            return _evaluators[sid]
        if len(_evaluators) >= _MAX_SESSIONS:
            _evaluators.popitem(last=False)

        ev = ExpressionEvaluator()
        _evaluators[sid] = ev
        return ev

@main_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@main_bp.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json(silent=True) or {}
    expr = (data.get("expression") or "").strip()
    stateful = bool(data.get("stateful", True))

    if not expr:
        return jsonify({"ok": False, "error": "Пустое выражение"}), 400
    if len(expr) > current_app.config["MAX_EXPRESSION_LENGTH"]:
        return jsonify({"ok": False, "error": "Выражение слишком длинное"}), 400

    evaluator = _get_evaluator() if stateful else ExpressionEvaluator()

    try:
        result = evaluator.run(expr)
    except MatrixError as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }), 400
    except Exception:
        current_app.logger.exception("Unexpected error in /calculate")
        return jsonify({
            "ok": False,
            "error": "Внутренняя ошибка сервера",
            "error_type": "ServerError",
        }), 500

    history = evaluator.history[-current_app.config["MAX_HISTORY_ITEMS"]:]

    payload = {
        "ok": True,
        "result": format_result(result),
        "history": [
            {"expr": expr_str, "pretty": format_result(res)["pretty"]}
            for expr_str, res in history
        ],
    }

    if stateful:
        payload["variables"] = {
            name: format_result(val)["pretty"]
            for name, val in evaluator.env.items()
        }

    return jsonify(payload)

@main_bp.route("/reset", methods=["POST"])
def reset():
    sid = session.get("sid")
    if sid:
        with _evaluators_lock:
            _evaluators.pop(sid, None)
    return jsonify({"ok": True, "message": "Состояние сброшено"})