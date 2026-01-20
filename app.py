from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import json
import os
import re
from dotenv import load_dotenv
from fir_prompt import build_prompt
from pdf_generator import generate_pdf

load_dotenv()

app = Flask(__name__)
CORS(app)

# =========================================================
# AUTO FIX JSON (MOST IMPORTANT)
# =========================================================
def auto_fix_json(text: str) -> str:
    """
    Fix common LLM JSON issues:
    - Missing closing brace
    - Leading/trailing garbage text
    """
    if not text:
        return ""

    text = text.strip()

    # Keep only content starting from first {
    start = text.find("{")
    if start != -1:
        text = text[start:]

    # Auto close JSON if missing
    if text.startswith("{") and not text.endswith("}"):
        text += "}"

    return text


# =========================================================
# SAFE JSON LOAD
# =========================================================
def safe_json_loads(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Remove trailing commas if any
        cleaned = re.sub(r",\s*}", "}", text)
        cleaned = re.sub(r",\s*]", "]", cleaned)
        return json.loads(cleaned)


# =========================================================
# HEALTH CHECK
# =========================================================
@app.route("/safe", methods=["GET"])
def safe():
    return jsonify({
        "status": "OK",
        "message": "Server is running",
        "endpoint": "/generate-fir (POST)"
    })


# =========================================================
# PDF DOWNLOAD
# =========================================================
@app.route("/download/<path:filename>", methods=["GET"])
def download_pdf(filename):
    if not os.path.exists(filename):
        return jsonify({"error": "PDF file not found"}), 404
    return send_file(filename, as_attachment=False)


# =========================================================
# FIR GENERATION API
# =========================================================
@app.route("/generate-fir", methods=["POST"])
def generate_fir():
    try:
        data = request.json
        print("DATA FROM BROWSER:", data)

        if not data:
            return jsonify({"error": "No JSON body received"}), 400

        # ---------------- Build Prompt ----------------
        prompt = build_prompt(data)

        # ---------------- Call Groq API ----------------
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system",
                        "content": "Return ONLY valid raw JSON. No explanation. No extra text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2
            },
            timeout=30
        )

        if response.status_code != 200:
            return jsonify({
                "error": "LLM API failed",
                "details": response.text
            }), 500

        # ---------------- READ AI OUTPUT ----------------
        ai_text = response.json()["choices"][0]["message"]["content"]

        # ---------------- FIX & PARSE JSON ----------------
        ai_text = auto_fix_json(ai_text)

        try:
            fir_json = safe_json_loads(ai_text)
        except Exception as e:
            return jsonify({
                "error": "Invalid JSON returned by AI",
                "raw_ai_response": ai_text,
                "details": str(e)
            }), 500

        # ---------------- VALIDATION ----------------
        if "fir_text" not in fir_json:
            return jsonify({
                "error": "AI JSON missing fir_text",
                "parsed_json": fir_json
            }), 500

        # ---------------- MERGE FRONTEND DATA ----------------
        fir_json["name"] = data.get("name")
        fir_json["mobile"] = data.get("mobile")
        fir_json["address"] = data.get("address")
        fir_json["pincode"] = data.get("pincode")

        # ---------------- GENERATE PDF ----------------
        pdf_path = generate_pdf(fir_json)

        if not pdf_path or not os.path.exists(pdf_path):
            return jsonify({"error": "PDF generation failed"}), 500

        # ---------------- SUCCESS ----------------
        return jsonify({
            "status": "success",
            "crime_type": fir_json.get("crime_type"),
            "ipc_sections": fir_json.get("ipc_sections"),
            "it_act_sections": fir_json.get("it_act_sections"),
            "pdf": pdf_path
        })

    except Exception as e:
        return jsonify({
            "error": "Server error",
            "details": str(e)
        }), 500


# =========================================================
# RUN SERVER
# =========================================================
if __name__ == "__main__":
    app.run(port=5000, debug=True)
