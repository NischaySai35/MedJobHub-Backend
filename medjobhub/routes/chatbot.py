# chatbot.py (updated)
from medjobhub import app, session, jsonify, cross_origin, allowed_url, request
from medjobhub.models import User, Job, JobApplication
from medjobhub.routes.profile import get_current_user_profile
import google.generativeai as genai
import json
import logging
from flask import stream_with_context, Response

# ensure logger prints debug messages (optional)
app.logger.setLevel(logging.DEBUG)


@app.route("/chatbot_stream", methods=["GET"])
def chatbot_stream():
    # Quick auth guard
    if "user_id" not in session:
        app.logger.info("[STREAM] unauthorized request to /chatbot_stream")
        return Response("Unauthorized", status=401)

    # SSE uses GET; message passed as query param
    user_msg = request.args.get("message", "") or ""
    user_id = session.get("user_id")
    app.logger.info("[STREAM] incoming chat stream request user_id=%s msg_len=%d", user_id, len(user_msg))

    # --- Load data (profile, jobs, apps) ---
    try:
        user = User.query.get(user_id)
        role = getattr(user, "role", "job_seeker")
    except Exception as e:
        app.logger.exception("[STREAM] failed to fetch user")
        return Response("Server error", status=500)

    try:
        prof_data = get_current_user_profile().json
        profile = prof_data.get("user", {}) if isinstance(prof_data, dict) else {}
    except Exception as e:
        app.logger.exception("[STREAM] failed to fetch profile")
        profile = {}

    try:
        jobs = [j.to_dict() for j in Job.query.all()]
    except Exception as e:
        app.logger.exception("[STREAM] failed to fetch jobs")
        jobs = []

    try:
        if role == "employer":
            apps_q = JobApplication.query.join(Job).filter(Job.posted_by == user.id).all()
        else:
            apps_q = JobApplication.query.filter_by(user_id=user.id).all()
        apps = [a.to_dict() for a in apps_q]
    except Exception as e:
        app.logger.exception("[STREAM] failed to fetch applications")
        apps = []

    app.logger.debug("[STREAM] profile keys: %s", list(profile.keys()) if isinstance(profile, dict) else str(type(profile)))
    app.logger.debug("[STREAM] jobs_count=%d apps_count=%d", len(jobs), len(apps))
    if len(jobs) > 0:
        app.logger.debug("[STREAM] jobs sample: %s", json.dumps(jobs[:2], indent=2))
    if len(apps) > 0:
        app.logger.debug("[STREAM] apps sample: %s", json.dumps(apps[:2], indent=2))

    # --- System prompt (PARA protocol instructions) ---
    system_prompt = f"""
You are MedJobHub's AI Assistant.

USER ROLE: {role}

USER PROFILE:
{json.dumps(profile, indent=2)}

ALL JOBS:
{json.dumps(jobs, indent=2)}

USER APPLICATIONS:
{json.dumps(apps, indent=2)}

IMPORTANT STREAMING FORMAT:
- Respond using <PARA> blocks for human-readable paragraphs.
- Each <PARA> must contain a full paragraph (no partial sentences).
- Never split words across blocks.
- Do NOT repeat content in multiple <PARA> blocks. Each <PARA> must continue smoothly from the previous one.
- After all <PARA> blocks, output ONE <JSON> block with only the final JSON payload.

When the user asks:
- "take me to job applications" → produce final JSON action for "/job-applications"
- "go to available jobs" → final JSON action "/jobs"
similarly for "/profile", "/about", "/contact-us", home ("/").
- "how many jobs", "jobs from X", "skills to improve" → analyze and respond.

Final JSON format (wrapped in <JSON>...</JSON>):
<JSON>
{{
  "reply": "<short human summary>",
  "action": null OR {{
      "type": "NAVIGATE",
      "url": "<path>"
  }}
}}
</JSON>
"""

    app.logger.debug("Full SYSTEM PROMPT (stream) length=%d", len(system_prompt))

    # --- Generator that yields SSE data frames ---
    def generate():
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            # start streaming from the model
            resp = model.generate_content(system_prompt + "\nUSER: " + user_msg, stream=True)

            buffer = ""
            for chunk in resp:
                # chunk.text may be None or empty; use getattr safely
                text = getattr(chunk, "text", None)
                if not text:
                    continue

                buffer += text

                # emit all complete <PARA> blocks found in buffer
                while "<PARA>" in buffer and "</PARA>" in buffer:
                    start = buffer.index("<PARA>") + len("<PARA>")
                    end = buffer.index("</PARA>")
                    para = buffer[start:end].strip()
                    buffer = buffer[end + len("</PARA>"):]
                    app.logger.debug("[STREAM] emitting PARA (len=%d)", len(para))
                    yield f"data: {json.dumps({'sender': 'bot', 'text': para})}\n\n"

                # detect final JSON block and finish
                if "<JSON>" in buffer and "</JSON>" in buffer:
                    start = buffer.index("<JSON>") + len("<JSON>")
                    end = buffer.index("</JSON>")
                    json_block = buffer[start:end].strip()
                    buffer = ""  # clear leftover
                    app.logger.debug("[STREAM] emitting FINAL JSON")
                    yield f"data: {json.dumps({'sender': 'final', 'text': json_block})}\n\n"
                    return  # end generator after final JSON

            # If loop ends without a final JSON, but we have leftover text, emit it as a PARA
            if buffer.strip():
                app.logger.debug("[STREAM] emitting leftover PARA at end (len=%d)", len(buffer.strip()))
                yield f"data: {json.dumps({'sender': 'bot', 'text': buffer.strip()})}\n\n"

        except Exception as e:
            # Log and inform client gracefully
            app.logger.exception("[STREAM] exception during generation")
            err_msg = "⚠️ The AI stream encountered an error. Please try again."
            try:
                yield f"data: {json.dumps({'sender': 'bot', 'text': err_msg})}\n\n"
            except Exception:
                # If yielding fails, just stop
                app.logger.exception("[STREAM] failed to send error message")

        finally:
            # Always signal end-of-stream
            yield "data: [DONE]\n\n"

    # Return SSE response (Flask Response supports streaming iterables)
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
