from __future__ import annotations
from typing import Annotated

import os
import model_dev
from dotenv import load_dotenv
from flask import Flask, jsonify, request, Response, stream_with_context, session
from flask_cors import CORS

load_dotenv() 

app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

new_rag = model_dev.rag_model()
question = ""

@app.route("/api/test/", methods = ["GET"])
def test_api():
    question = "What's your name?"
    return jsonify({"status": 200, "info": "API Connected!"})

@app.route("/api/test/stream/", methods = ["GET"])
def model_stream():
    stream = new_rag.stream_model(question)
    return Response(stream_with_context(stream), mimetype='text/event-stream')

@app.route("/api/agent/stream/", methods = ["GET"])
def agent_stream():
    stream = new_rag.stream_agent(question)
    return Response(stream_with_context(stream), mimetype='text/event-stream')

@app.route("/api/question/", methods = ["POST"])
def update_question():
    question = request.form.get("question")
    return jsonify({"status": 200, "info": "Question Updated!"})

@app.route("/api/upload/csv/", methods = ["GET", "POST", "PUT"])
def upload_csv():
    try:
        file = request.files['file']
        new_rag.fill_database(file)
        return jsonify({"status": 200, "info": "File uploaded to Vector Database!"})
    except Exception as e:
        return jsonify({"status": 500, "info": f"Error: {e}"})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

if __name__ == "__main__":
    app.secret_key = os.getenv("SECRET_KEY")

    app.run(threaded = True)