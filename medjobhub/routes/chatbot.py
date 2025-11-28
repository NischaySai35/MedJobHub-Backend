from medjobhub import app, session, jsonify, cross_origin, allowed_url, request
from medjobhub.models import User, Job, JobApplication
from medjobhub.routes.profile import get_current_user_profile
import google.generativeai as genai
import json
import logging
from flask import stream_with_context, Response

# ensure logger prints debug messages (optional)
app.logger.setLevel(logging.DEBUG)

@app.route("/chatbot", methods=["POST", "OPTIONS"])
@cross_origin(origin=allowed_url, supports_credentials=True)
def chatbot():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user_msg = data.get("message", "")

    # fetch user
    user = User.query.get(session["user_id"])
    role = user.role

    # fetch profile
    profile = {}
    prof_data = get_current_user_profile().json
    if prof_data.get("success"):
        profile = prof_data["user"]

    # fetch jobs
    jobs = [j.to_dict() for j in Job.query.all()]

    # fetch apps
    if role == "employer":
        apps = JobApplication.query.join(Job).filter(Job.posted_by == user.id).all()
    else:
        apps = JobApplication.query.filter_by(user_id=user.id).all()
    apps = [a.to_dict() for a in apps]

    # Log fetched data so you can see it in the server console
    app.logger.info("Chatbot request from user_id=%s role=%s message=%s", session.get("user_id"), role, user_msg)
    app.logger.debug("Profile: %s", json.dumps(profile, indent=2))
    app.logger.debug("Jobs count=%d", len(jobs))
    app.logger.debug("Jobs (sample): %s", json.dumps(jobs[:3], indent=2))
    app.logger.debug("Applications count=%d", len(apps))
    app.logger.debug("Applications (sample): %s", json.dumps(apps[:3], indent=2))

    system_prompt = f"""
    You are MedJobHub's AI Assistant.

    USER ROLE: {role}

    USER PROFILE:
    {json.dumps(profile, indent=2)}

    ALL JOBS:
    {json.dumps(jobs, indent=2)}

    USER APPLICATIONS:
    {json.dumps(apps, indent=2)}

    When the user asks:
    - "take me to job applications" → respond with JSON:
      {{"reply": "Taking you there!", "action": {{"type": "NAVIGATE", "url": "/job-applications"}}}})

    - "go to available jobs" → "/job-listings"

    - Queries like "how many jobs?", "jobs from xyz", "jobs for nurses":
      → analyze the jobs list and reply.

    - If job_seeker asks "what skills should I improve for this job?"
      → read job.required_qualifications & job.specialization & compare with user.skills.

    Your answer MUST be JSON:
    {{
      "reply": "<normal human reply>",
      "action": null OR {{
         "type": "NAVIGATE",
         "url": "<frontend route>"
      }}
    }}
    """

    # print full system prompt to console so you can verify everything sent to the model
    app.logger.debug("Full SYSTEM PROMPT:\n%s", system_prompt)

    model = genai.GenerativeModel("gemini-2.0-flash")

    result = model.generate_content(
        system_prompt + "\nUser: " + user_msg
    )

    try:
        text = result.text.strip()
        # extract JSON
        start = text.find("{")
        end = text.rfind("}") + 1
        parsed = json.loads(text[start:end])
        return jsonify(parsed)
    except:
        return jsonify({"reply": result.text, "action": None})
    



@app.route("/chatbot_stream", methods=["GET"])
def chatbot_stream():
    if "user_id" not in session:
        return Response("Unauthorized", status=401)

    # message comes from query string (SSE GET cannot have a body)
    user_msg = request.args.get("message", "")

    # fetch user
    user = User.query.get(session["user_id"])
    role = user.role

    # fetch profile
    prof_data = get_current_user_profile().json
    profile = prof_data.get("user", {})

    # fetch jobs
    jobs = [j.to_dict() for j in Job.query.all()]

    # fetch applications
    if role == "employer":
        apps = JobApplication.query.join(Job).filter(Job.posted_by == user.id).all()
    else:
        apps = JobApplication.query.filter_by(user_id=user.id).all()

    apps = [a.to_dict() for a in apps]

    # SYSTEM PROMPT
    system_prompt = f"""
        You are MedJobHub's AI Assistant.

        USER ROLE: {role}

        USER PROFILE:
        {json.dumps(profile, indent=2)}

        ALL JOBS:
        {json.dumps(jobs, indent=2)}

        USER APPLICATIONS:
        {json.dumps(apps, indent=2)}

        IMPORTANT:
        - During streaming, first send normal human-readable text only.
        - Output your response in multiple <PARA> blocks.
        - Each <PARA> contains a full paragraph (never partial sentences).
        - Never split words across blocks.
        - After finishing, send ONE final JSON object starting with <JSON>.

        When the user asks:
        - "take me to job applications" → return JSON: {{"reply": "Taking you there!", "action": {{"type": "NAVIGATE", "url": "/job-applications"}}}}
        - "go to available jobs" → navigate to "/job-listings"
        - Queries like "how many jobs?", "jobs from xyz", etc → analyze jobs
        - Skills improvement → compare job requirements with user skills

        Your final JSON MUST be in this format:
        <JSON>
        {{
            "reply": "<message>",
            "action": null OR {{
                "type": "NAVIGATE",
                "url": "<path>"
            }}
        }}
    """
    # print full system prompt for streaming endpoint as well
    app.logger.debug("Full SYSTEM PROMPT (stream):\n%s", system_prompt)

    def generate():
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content(system_prompt + "\nUSER: " + user_msg, stream=True)

        buffer = ""

        for chunk in resp:
            if not chunk.text:
                continue
            buffer += chunk.text

            # Process <PARA> blocks
            while "<PARA>" in buffer and "</PARA>" in buffer:
                start = buffer.index("<PARA>") + 6
                end = buffer.index("</PARA>")
                para = buffer[start:end].strip()
                buffer = buffer[end + len("</PARA>"):]
                yield f"data: {json.dumps({'sender': 'bot', 'text': para})}\n\n"

            # Process <JSON> block (END)
            if "<JSON>" in buffer and "</JSON>" in buffer:
                start = buffer.index("<JSON>") + 6
                end = buffer.index("</JSON>")
                json_block = buffer[start:end].strip()
                buffer = ""  # reset unused text
                yield f"data: {json.dumps({'sender': 'final', 'text': json_block})}\n\n"
                break  # final message

        yield "data: [DONE]\n\n"
