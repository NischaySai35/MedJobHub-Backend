from flask import request, jsonify
from medjobhub import app, session, cross_origin
import os, json
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@app.route("/ai-job-matcher", methods=["POST", "OPTIONS"])
@cross_origin(origins=["http://localhost:5173"], supports_credentials=True, 
              allow_headers=["Content-Type", "Authorization"])
def ai_job_matcher():
    data = request.json
    profile = data.get("profile")
    jobs = data.get("jobs")

    if not profile or not jobs:
        return jsonify({"error": "Missing data"}), 400

    # 🧩 Build a compact prompt for Gemini
    prompt = f"""
    You are an AI job recommendation engine.

    Given the job seeker's profile:
    Skills: {profile.get('skills')}
    Education: {profile.get('education')}
    Experience: {profile.get('experience')}
    Certifications: {profile.get('certifications')}
    Specialization: {profile.get('specialization')}
    Availability: {profile.get('availability')}

    Rank the following jobs (in JSON only) by how well they match the user's profile.
    Consider skill match, specialization, and experience relevance.
    Analyze the following jobs and rank them by how well they match the user's profile.
    Explain the reasoning briefly for each job (mention which skills or experience matched most strongly).

    Return only valid JSON in this format:

    {{
    "ranked_jobs": [
        {{
        "id": <job_id>,
        "match_score": <0-100>,
        "reason": "<one-line reason why this job was ranked here>"
        }},
        ...
    ]
    }}
    """

    model = genai.GenerativeModel("gemini-2.5-flash")  # fast & cheap

    try:
        content = f"""
        You are a ranking assistant that outputs clean JSON only.

        {prompt}

        Jobs JSON:
        {json.dumps(jobs, indent=2)}
        """

        result = model.generate_content(content)

        # Attempt to parse Gemini output
        text = result.text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        json_str = text[start:end]

        ai_output = json.loads(json_str)
        ranked_jobs = ai_output.get("ranked_jobs", [])

        # Sort jobs by match_score descending
        ranked_jobs = sorted(ranked_jobs, key=lambda j: j.get("match_score", 0), reverse=True)

        # 🧠 Debug print - show reasoning
        for r in ranked_jobs:
            print(f"🔹 Job ID {r.get('id')}: {r.get('reason', 'No reason provided')} (Score: {r.get('match_score', '?')})")

        return jsonify({"ranked_jobs": ranked_jobs})


    except Exception as e:
        print("Gemini parsing error:", e)
        return jsonify({"ranked_jobs": jobs})  # fallback
