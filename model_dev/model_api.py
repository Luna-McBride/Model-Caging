from __future__ import annotations
from typing import Annotated

import importlib.util
import os
from pathlib import Path
from dotenv import load_dotenv

from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS
from model_dev import rag_model

load_dotenv()

app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

def import_rust_module():
    root = Path(__file__).resolve().parent
    rust_release = root / "model_rust" / "target" / "release"
    if not rust_release.exists():
        raise ImportError("Rust extension directory not found: model_rust/target/release")

    module_path = None
    for pattern in ["model_rust*.so", "libmodel_rust*.so"]:
        candidates = sorted(rust_release.glob(pattern))
        if candidates:
            module_path = candidates[0]
            break

    if module_path is None:
        raise ImportError("Could not find compiled Rust module in model_rust/target/release")

    spec = importlib.util.spec_from_file_location("model_rust", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load Rust module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

rust_module = import_rust_module()
PyRagModel = rust_module.PyRagModel
rag = rag_model()
question = ""

@app.route("/api/test/", methods=["GET"])
def test_api():
    question = "What's your name?"
    return jsonify({"status": 200, "info": "API Connected!"})

@app.route("/api/test/stream/", methods=["GET"])
def model_stream():
    print(f"[Flask] model_stream question={question}")

    def event_stream():
        try:
            # Use Python LLM directly for text generation
            for chunk in rag.stream_model(question):
                yield f"data: {chunk}\n\n"
        except Exception as exc:
            print(f"[Flask] model_stream error: {exc}")
            yield f"data: ERROR: {exc}\n\n"

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream')

@app.route("/api/agent/stream/", methods=["GET"])
def agent_stream():
    print(f"[Flask] agent_stream question={question}")

    def event_stream():
        try:
            # Use Python LLM with RAG for context-aware answer generation
            for chunk in rag.stream_agent(question):
                yield f"{chunk}\n\n"
        except Exception as exc:
            print(f"[Flask] agent_stream error: {exc}")
            yield f"data: ERROR: {exc}\n\n"

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream')

@app.route("/api/question/", methods=["POST"])
def update_question():
    global question
    question = request.get_json(force = True, silent=True).get("question")
    print(f"[Flask] updated question={question}")
    return jsonify({"status": 200, "info": "Question Updated!"})

@app.route("/api/upload/csv/", methods=["GET", "POST", "PUT"])
def upload_csv():
    try:
        file = request.files['file']
        print(f"[Flask] upload_csv content_length={len(file.getvalue()) if hasattr(file, 'getvalue') else 'unknown'}")
        rag.fill_database(file)
        return jsonify({"status": 200, "info": "File uploaded to Vector Database!"})
    except Exception as e:
        print(f"[Flask] upload_csv error: {e}")
        return jsonify({"status": 500, "info": f"Error: {e}"})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

if __name__ == "__main__":
    app.run(threaded=True)
