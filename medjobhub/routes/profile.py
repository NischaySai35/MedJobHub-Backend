from medjobhub import app, db, session, jsonify, request, cross_origin, allowed_url
from medjobhub.models import User, UserProfile
import cloudinary.uploader
from medjobhub.routes.upload_cloudinary import upload_files_to_cloudinary
from flask import Blueprint, request, send_file, render_template_string
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os
import requests
from io import BytesIO
from datetime import datetime
from weasyprint import HTML

@app.route('/current_user_profile', methods=['GET', 'OPTIONS'])
@cross_origin(origin="http://localhost:5173", supports_credentials=True)
def get_current_user_profile():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Please sign in to access profile"})
    
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({"success": False, "message": "User not found"})
        
        user_profile = UserProfile.query.filter_by(user_id=user.id).first()
        
        user_data = {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "gender": user.gender,
            "age": user.age,
            "address": user.address,
            "role": user.role,
            "company_name": user.company_name,
            "resume": user.resume,
            "is_verified": user.is_verified,
        }
        
        if user_profile:
            user_data.update({
                "profile_pic_url": user_profile.profile_pic_url,
                "linkedin": user_profile.linkedin,
                "github": user_profile.github,
                "twitter": user_profile.twitter,
                "portfolio_website": user_profile.portfolio_website,
                "medical_license_number": user_profile.medical_license_number,
                "specialization": user_profile.specialization,
                "certifications": user_profile.certifications,
                "skills": user_profile.skills,
                "education": user_profile.education,
                "work_experience": user_profile.work_experience,
                "publications": user_profile.publications,
                "availability": user_profile.availability,
                "resume_url": user_profile.resume_url,
                "company_website": user_profile.company_website,
                "company_description": user_profile.company_description,
                "industry": user_profile.industry,
                "company_size": user_profile.company_size,
                "founded_year": user_profile.founded_year,
                "headquarters_location": user_profile.headquarters_location,
                "company_logo": user_profile.company_logo,
            })
        
        return jsonify({
            "success": True,
            "user": user_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching profile: {str(e)}"
        })

@app.route('/update_profile', methods=['POST', 'OPTIONS'])
@cross_origin(origin="http://localhost:5173", supports_credentials=True)
def update_profile():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Please sign in to update profile"})
    
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({"success": False, "message": "User not found"})
        
        data = request.get_json()
        
        basic_fields = ['first_name', 'last_name', 'phone', 'gender', 'age', 'address', 'company_name']
        for field in basic_fields:
            if field in data:
                setattr(user, field, data[field])
        
        user_profile = UserProfile.query.filter_by(user_id=user.id).first()
        if not user_profile:
            user_profile = UserProfile(
                user_id=user.id,
                first_name=user.first_name or "",
                last_name=user.last_name or ""
            )
            db.session.add(user_profile)
        
        profile_fields = [
            'profile_pic_url', 'linkedin', 'github', 'twitter', 'portfolio_website',
            'medical_license_number', 'specialization', 'certifications', 'skills',
            'education', 'work_experience', 'publications', 'availability', 'resume_url',
            'company_website', 'company_description', 'industry', 'company_size',
            'founded_year', 'headquarters_location', 'company_logo'
        ]
        
        for field in profile_fields:
            if field in data:
                setattr(user_profile, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Profile updated successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Error updating profile: {str(e)}"
        })

@app.route('/upload_profile_picture', methods=['POST', 'OPTIONS'])
@cross_origin(origin="http://localhost:5173", supports_credentials=True)
def upload_profile_picture():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Please sign in to upload profile picture"})
    
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({"success": False, "message": "User not found"})
        
        if 'profile_pic' not in request.files:
            return jsonify({"success": False, "message": "No file provided"})
        
        file = request.files['profile_pic']
        if file.filename == '':
            return jsonify({"success": False, "message": "No file selected"})
        
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):

            upload_result = cloudinary.uploader.upload(
                file,
                folder="profile_pictures",
                resource_type="image",
                transformation=[
                    {"width": 300, "height": 300, "crop": "fill", "gravity": "face"},
                    {"quality": "auto", "fetch_format": "auto"}
                ]
            )
            
            profile_pic_url = upload_result['secure_url']
            
            user_profile = UserProfile.query.filter_by(user_id=user.id).first()
            if not user_profile:
                user_profile = UserProfile(
                    user_id=user.id,
                    first_name=user.first_name or "",
                    last_name=user.last_name or ""
                )
                db.session.add(user_profile)
            
            user_profile.profile_pic_url = profile_pic_url
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Profile picture uploaded successfully",
                "profile_pic_url": profile_pic_url
            })
        else:
            return jsonify({"success": False, "message": "Invalid file type. Please upload an image file."})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Error uploading profile picture: {str(e)}"
        })
    
@app.route("/generate_resume", methods=["GET"])
@cross_origin(origin="http://localhost:5173", supports_credentials=True)
def generate_resume():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get(session["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_profile = UserProfile.query.filter_by(user_id=user.id).first()
    print("Fetched UserProfile:", user_profile)

    if not user_profile:
        return jsonify({"error": "Profile not found"}), 404

    # ✅ Merge user_profile fields into user for easy access
    if user_profile:
        for field in [
            "medical_license_number", "education", "work_experience",
            "certifications", "skills", "linkedin", "github",
            "twitter", "portfolio_website"
        ]:
            if getattr(user_profile, field, None):
                setattr(user, field, getattr(user_profile, field))


    profile_pic = user_profile.profile_pic_url if getattr(user_profile, "profile_pic_url", None) else None

    # ✅ HTML Resume Template
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: sans-serif;
                background: #f9fbfd;
                color: #333;
                margin: 0;
                padding: 0;
            }}
            .resume {{
                width: 100%;
                margin: 0;
                background: white;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                padding: 5px 8px;
            }}
            .header {{
                text-align: center;
            }}
            .profile-pic {{
                width: 120px;
                height: 120px;
                border-radius: 50%;
                object-fit: cover;
                border: 4px solid #007bff;
                margin-bottom: 10px;
            }}
            .no-pic {{
                width: 120px;
                height: 120px;
                border-radius: 50%;
                border: 3px dashed #007bff;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #007bff;
                font-weight: bold;
                margin: 0 auto 10px auto;
            }}
            h1 {{
                color: #007bff;
                font-size: 26px;
                margin-bottom: 4px;
            }}
            .subtitle {{
                color: gray;
                font-size: 14px;
                margin-bottom: 10px;
            }}
            .contact {{
                font-size: 13px;
                color: #555;
                margin-bottom: 20px;
            }}
            hr {{
                border: none;
                border-top: 2px solid #007bff;
                margin: 20px 0;
            }}
            .section-title {{
                color: #007bff;
                font-size: 18px;
                margin-top: 20px;
                font-weight: 600;
                border-left: 4px solid #007bff;
                padding-left: 10px;
            }}
            .section-content {{
                margin-top: 8px;
                font-size: 14px;
                color: #333;
                line-height: 1.6;
            }}
            .links a {{
                color: #007bff;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="resume">
            <div class="header">
                {"<img src='" + profile_pic + "' class='profile-pic'>" if profile_pic else "<div class='no-pic'>No Photo</div>"}
                <h1>{user.first_name or ''} {user.last_name or ''}</h1>
                <div class="subtitle">{user.role or 'Professional'}</div>
                <div class="contact">📧 {user.email or 'N/A'} &nbsp; | &nbsp; 📞 {user.phone or 'N/A'}</div>
            </div>

            <hr/>

            <div class="section">
                <div class="section-title">👤 Gender & Age</div>
                <div class="section-content">{user.gender or 'N/A'}, {user.age or 'N/A'} years old</div>

                <div class="section-title">📍 Address</div>
                <div class="section-content">{user.address or 'Not provided'}</div>

                <div class="section-title">🏥 Medical License</div>
                <div class="section-content">{getattr(user, "medical_license_number", "Not provided")}</div>

                <div class="section-title">🎓 Education</div>
                <div class="section-content">{getattr(user, "education", "Not provided")}</div>

                <div class="section-title">💼 Work Experience</div>
                <div class="section-content">{getattr(user, "work_experience", "Not provided")}</div>

                <div class="section-title">🏅 Certifications</div>
                <div class="section-content">{getattr(user, "certifications", "Not provided")}</div>

                <div class="section-title">🔧 Skills</div>
                <div class="section-content">{getattr(user, "skills", "Not provided")}</div>

                <div class="section-title">🔗 Online Profiles</div>
                <div class="section-content links">
                    LinkedIn: {getattr(user, "linkedin_profile", "Not provided")}<br/>
                    GitHub: {getattr(user, "github_profile", "Not provided")}<br/>
                    Twitter: {getattr(user, "twitter_profile", "Not provided")}<br/>
                    Portfolio: {getattr(user, "portfolio_website", "Not provided")}
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    # ✅ Convert HTML → PDF
    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)

    return send_file(pdf_buffer, as_attachment=True, download_name=f"{user.first_name}_Resume.pdf", mimetype="application/pdf")
