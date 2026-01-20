def build_prompt(data):
    return f"""
You are an Indian Cyber Crime Police Legal Expert.

STRICT OUTPUT RULES (FOLLOW EXACTLY):
- Output MUST start with {{ and MUST end with }}
- Output ONLY valid JSON (no markdown, no explanation)
- Do NOT include father name, guardian name, or relations (no s/o, d/o, w/o)
- Do NOT repeat complainant details separately inside fir_text
- Do NOT create a separate "Victim Details" section
- Do NOT mention IPC sections or IT Act sections inside fir_text
- Do NOT add LR number, police station name, or officer name
- Do NOT include headings, titles, or numbered points inside fir_text
- Do NOT include dates in FIR number format
- Do NOT include signatures or investigation officer details
- Do NOT include any text outside JSON
- Do NOT include trailing commas
- All new lines in fir_text MUST be written as \\n
- fir_text must be concise (maximum 10–12 lines)

IMPORTANT FORMATTING FOR SECTIONS:
- ipc_sections MUST contain ONLY section numbers as strings (example: "420", "468")
- it_act_sections MUST contain ONLY section numbers as strings (example: "66C", "66D")
- Do NOT include words like IPC, IT Act, Information Technology Act inside arrays
- Capitalization and full law names will be handled later by the system

FIR TEXT STYLE RULES:
- Write in first person ("I")
- Use simple, formal police language
- Mention place and pincode only once
- Split the FIR narration into 2–3 short paragraphs
- Use exactly "\\n\\n" between paragraphs
- End FIR text with a request for necessary legal action and recovery of the fraudulently debited amount as per law


TASK:
1. Identify crime_type (simple, title case wording)
2. Identify applicable IPC sections (numbers only)
3. Identify applicable IT Act sections (numbers only)
4. Generate a concise FIR narration (NO sections, NO headings)

INCIDENT DETAILS:
Incident: {data['incident']}

COMPLAINANT DETAILS (USE ONLY THESE — DO NOT INVENT):
Name: {data['name']}
Mobile: {data['mobile']}
Address: {data['address']}
Pincode: {data['pincode']}

OUTPUT JSON SCHEMA (MANDATORY):
{{
  "crime_type": "string",
  "ipc_sections": ["string"],
  "it_act_sections": ["string"],
  "fir_text": "string"
}}

FINAL REMINDER:
Return ONLY the JSON object.
Nothing before it.
Nothing after it.
"""
