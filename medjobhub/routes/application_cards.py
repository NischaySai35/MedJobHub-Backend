from medjobhub import app, session, db, Mail,datetime,cross_origin,allowed_url
from flask import request, jsonify
from flask_mail import Message
from medjobhub.models import JobApplication, Job

mail = Mail(app)

#Employer_Applications
@app.route('/employer_applications', methods=['GET'])
@cross_origin(origin=allowed_url, supports_credentials=True)
def employer_applications():
    if 'user_id' not in session or session['role'] != 'employer':
        return jsonify({"success": False, "message": "Unauthorized access."})
    
    user_id = session['user_id']
    applications = JobApplication.query.join(Job).filter(Job.posted_by == user_id).all()
    applications_data = [app.to_dict() for app in applications]
    
    return jsonify({"success": True, "applications": applications_data})



#Update Application
@app.route('/update_application/<int:application_id>', methods=['POST'])
@cross_origin(origin=allowed_url, supports_credentials=True)
def update_application_status(application_id):
    if 'user_id' not in session or session['role'] != 'employer':
        return jsonify({"success": False, "message": "Unauthorized access."})
    
    application = JobApplication.query.get(application_id)
    if not application:
        return jsonify({"success": False, "message": "Application not found."})
    
    new_status = request.json.get('status')
    application.application_status = new_status
    
    if new_status == "Rejected":
        db.session.delete(application)
        db.session.commit()
        msg = Message("Application Rejected - MedJobHub", sender="noreply@medjobhub.com", recipients=[application.email])
        msg.body = f"Dear {application.applicant_name},\n\nWe regret to inform you that your application has been rejected.\n\nBest Wishes,\nMedJobHub Team"
        mail.send(msg)
        return jsonify({"success": True, "message": "Application rejected and email sent."})
    
    db.session.commit()
    return jsonify({"success": True, "message": "Application status updated."})


#Apply_Job
@app.route('/apply_job/<int:job_id>', methods=['POST'])
def apply_job(job_id):
    if 'user_id' not in session or session['role'] == 'employer':
        return jsonify({"success": False, "message": "Unauthorized access"})
    
    job = Job.query.get(job_id)
    if not job:
        return jsonify({"success": False, "message": "Job not found"})
    
    data = request.get_json()
    application = JobApplication(
        job_id=job.id,
        user_id=session['user_id'],
        applicant_name=data.get('applicant_name'),
        email=data.get('email'),
        phone=data.get('phone'),
        resume_link=data.get('resume_link'),
        cover_letter=data.get('cover_letter'),
        qualifications=data.get('qualifications'),
        experience=data.get('experience'),
        preferred_shift=data.get('preferred_shift'),
        expected_salary=float(data.get('expected_salary', 0)),
        applied_on=datetime.utcnow(),
        application_status="Pending"
    )
    db.session.add(application)
    db.session.commit()
    return jsonify({"success": True, "message": "Application submitted successfully!"})


#Jobseeker_Applications
@app.route('/jobseeker_applications', methods=['GET'])
def jobseeker_applications():
    if 'user_id' not in session or session['role'] == 'employer':
        return jsonify({"success": False, "message": "Unauthorized access."})
    
    applications = JobApplication.query.filter_by(user_id=session.get('user_id')).all()
    applications_data = [app.to_dict() for app in applications]
    
    return jsonify({"success": True, "applications": applications_data})


#Delete_Applications
@app.route('/delete_application/<int:application_id>', methods=['POST'])
def delete_application(application_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized access."})
    
    application = JobApplication.query.get(application_id)
    if not application or application.user_id != session['user_id']:
        return jsonify({"success": False, "message": "Unauthorized action."})
    
    db.session.delete(application)
    db.session.commit()
    return jsonify({"success": True, "message": "Application withdrawn successfully."})
