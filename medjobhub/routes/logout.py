from medjobhub import app,session,jsonify,db,cross_origin,allowed_url
from medjobhub.models import User

#Logout
@app.route('/logout', methods=['POST'])
@cross_origin(origin=allowed_url, supports_credentials=True)
def logout():
    if "user_id" in session:
        user_id = session.pop("user_id", None)
        session.pop("role", None) 
        session.clear()  

        user = User.query.get(user_id)
        if user:
            user.is_verified = False 
            user.auth_token = None
            db.session.commit() 

        return jsonify({"success": True, "message": f"User of user_id:{user_id} logged out successfully."})
    else:
        return jsonify({"success": False, "message": "No active session found."})