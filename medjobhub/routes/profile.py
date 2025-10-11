from medjobhub import app, db, session, jsonify, request, cross_origin, allowed_url
from medjobhub.models import User, UserProfile
import cloudinary.uploader
from medjobhub.routes.upload_cloudinary import upload_files_to_cloudinary

@app.route('/current_user_profile', methods=['GET'])
@cross_origin(origin=allowed_url, supports_credentials=True)
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

@app.route('/update_profile', methods=['POST'])
@cross_origin(origin=allowed_url, supports_credentials=True)
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

@app.route('/upload_profile_picture', methods=['POST'])
@cross_origin(origin=allowed_url, supports_credentials=True)
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