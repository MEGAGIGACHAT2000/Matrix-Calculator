from flask import Blueprint, jsonify
from core import ExpressionEvaluator
from core.reference import REFERENCE

api_bp = Blueprint("api", __name__)

@api_bp.route("/version", methods=["GET"])
def version():
    return jsonify({
        "name": "matrix-calculator",
        "version": "1.0.0",
        "flask": True,
    })

@api_bp.route("/capabilities", methods=["GET"])
def capabilities():
    return jsonify({
        "functions": sorted(ExpressionEvaluator.FUNCTIONS.keys()),
        "attributes": sorted(ExpressionEvaluator.ATTRIBUTES.keys()),
        "operators": ["+", "-", "*", "/", "@", "**"],
        "examples": [
            "[[1,2],[3,4]] + [[5,6],[7,8]]",
            "A = [[1,2],[3,4]]; B = [[5,6],[7,8]]; A @ B",
            "det([[4,7],[2,6]])",
            "inv([[4,7],[2,6]])",
            "solve([[2,1],[-1,3]], [5, 10])",
            "[[1,2,3],[4,5,6]].T",
        ],
    })

@api_bp.route("/reference", methods=["GET"])
def reference():
    return jsonify(REFERENCE)