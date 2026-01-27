from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import json
import os
import re
from dotenv import load_dotenv
from fir_prompt import build_prompt
from pdf_generator import generate_pdf
from database import get_db, init_db
from datetime import datetime
import pytz



load_dotenv()

app = Flask(__name__)
CORS(app)

try:
    init_db()
except Exception as e:
    print("DB init skipped:", e)



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
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",   # required by OpenRouter
                "X-Title": "FIR Generator"             # any app name
            },
            json={
                "model": "meta-llama/llama-3.1-8b-instruct",
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
                "temperature": 0.2,
                "max_tokens": 700
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
        pdf_path, lr_no = generate_pdf(fir_json)

        if not pdf_path or not os.path.exists(pdf_path):
            return jsonify({"error": "PDF generation failed"}), 500
        
        # --------- CREATE IST TIMESTAMP ----------
        ist = pytz.timezone("Asia/Kolkata")
        created_at = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")

        
        # ================= SAVE USER DATA + PDF PATH TO DB =================
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO fir_cases (
        lr_no, name, mobile, address, pincode,
        incident, pdf_path, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
        lr_no,
        fir_json.get("name"),
        fir_json.get("mobile"),
        fir_json.get("address"),
        fir_json.get("pincode"),
        data.get("incident"),
        pdf_path,
        created_at
        ))


        conn.commit()
        conn.close()


        # ---------------- SUCCESS ----------------
        return jsonify({
            "status": "success",
            "crime_type": fir_json.get("crime_type"),
            "bns_sections": fir_json.get("bns_sections", []),
            "bnss_sections": fir_json.get("bnss_sections", []),
            "it_act_sections": fir_json.get("it_act_sections", []),
            "pdf": pdf_path
        })


    except Exception as e:
        return jsonify({
            "error": "Server error",
            "details": str(e)
        }), 500

@app.route("/records", methods=["GET"])
def view_fir_records():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            lr_no,
            name,
            mobile,
            address,
            pincode,
            incident,
            pdf_path,
            created_at
        FROM fir_cases
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()

    base_url = request.host_url.rstrip("/")

    results = []
    for row in rows:
        results.append({
            "lr_no": row["lr_no"],
            "name": row["name"],
            "mobile": row["mobile"],
            "address": row["address"],
            "pincode": row["pincode"],
            "incident": row["incident"],
            "pdf_url": f"{base_url}/download/{row['pdf_path']}",
            "created_at": row["created_at"]
        })

    return jsonify(results)

@app.route("/delete", methods=["DELETE"])
def reset_system():
    # delete DB data
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fir_cases")
    conn.commit()
    conn.close()

    # delete PDFs
    pdf_dir = "generated_fir"
    if os.path.exists(pdf_dir):
        for f in os.listdir(pdf_dir):
            if f.lower().endswith(".pdf"):
                os.remove(os.path.join(pdf_dir, f))

    return jsonify({
        "status": "success",
        "message": "Database and PDFs cleared"
    })




# =========================================================
# RUN SERVER
# =========================================================
if __name__ == "__main__":
    app.run(port=5000, debug=True)
