from flask import request, jsonify
from medjobhub import app, db, os, secure_filename, generate_password_hash,allowed_file
from medjobhub.models import User
from medjobhub.models import UserProfile
from werkzeug.exceptions import BadRequest
from .upload_cloudinary import upload_files_to_cloudinary

#SignIn
@app.route('/signup', methods=['POST'])
def signup():
    try:
        # JSON or FormData
        if request.content_type.startswith("application/json"):
            data = request.json
        elif request.content_type.startswith("multipart/form-data"):
            data = request.form
        else:
            return jsonify({"success": False, "message": "Invalid request format."})

        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        username = data.get('username', '').strip()
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        gender = data.get('gender')
        age = data.get('age')
        address = data.get('address', '').strip()
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        role = data.get('role')
        company_name = data.get('company_name', '').strip() if role == "employer" else None
        resume = None

        if not all([first_name, last_name, username, phone, email, gender, age, address, password, confirm_password, role]):
            return jsonify({"success": False, "message": "All fields are required."})

        if role not in ["employer", "job_seeker"]:
            return jsonify({"success": False, "message": "Invalid role selected."})

        if password != confirm_password:
            return jsonify({"success": False, "message": "Passwords do not match."})

        try:
            age = int(age)
        except ValueError:
            return jsonify({"success": False, "message": "Invalid age format."})

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            return jsonify({"success": False, "message": "Username or email already exists."})

        if role == "employer" and not company_name:
            return jsonify({"success": False, "message": "Company name is required for employers."})

        if role == "job_seeker" and 'resume' in request.files:
            file = request.files['resume']
            if file and allowed_file(file.filename):
                cloudinary_url = upload_files_to_cloudinary(file)  # Upload directly
                if not cloudinary_url:
                    return jsonify({"success": False, "message": "Failed to upload resume to Cloudinary."})
                resume = cloudinary_url
            else:
                return jsonify({"success": False, "message": "Invalid resume file format. Only PDF, DOC, DOCX allowed."})


        if role == "job_seeker" and not resume:
            return jsonify({"success": False, "message": "Resume is required for job seekers."})

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(
            first_name=first_name,
            last_name=last_name,
            username=username,
            phone=phone,
            email=email,
            gender=gender,
            age=age,
            address=address,
            password=hashed_password,
            role=role,
            company_name=company_name,
            resume=resume,
            is_verified=False
        )

        db.session.add(new_user)
        db.session.commit()
        # ✅ Automatically create an empty UserProfile right after signup

        user_profile = UserProfile(
            user_id=new_user.id,
            first_name=new_user.first_name or "",
            last_name=new_user.last_name or ""
        )
        db.session.add(user_profile)
        db.session.commit()


        return jsonify({
            "success": True,
            "message": "Your account has been created successfully! Please sign in to continue.",
            "username": username,
        }), 201

    except BadRequest:
        return jsonify({"success": False, "message": "Invalid request. Please check the form data."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
