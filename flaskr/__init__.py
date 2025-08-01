from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
import mariadb

def get_db_connection():
    try:
        conn = mariadb.connect(
            user="user",
            password="123",
            host="127.0.0.1",
            port=3305,
            database="db"
        )
        return conn
    except mariadb.Error as e:
        print(f"DB Connection Error: {e}")
        return None

app = Flask(__name__, instance_relative_config=True)
app.secret_key = "utc_secret_key_2025"

def get_user_by_credentials(email, password):
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, email, password, user_id, role, name, last_name, study_area, study_speciality, term FROM users WHERE email = ? AND password = ? AND is_active = TRUE", (email, password))
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user
    except mariadb.Error as e:
        print(f"Error al obtener usuario: {e}")
        return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/auth")
def auth():
    return render_template("auth.html")

@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json() if request.is_json else request.form
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        
        if not email or not password:
            return jsonify({
                "success": False,
                "message": "Email y contraseña son requeridos"
            }), 400
        
        user = get_user_by_credentials(email, password)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "Credenciales incorrectas"
            }), 401
        
        session["user_id"] = user[0]
        session["email"] = user[1]
        session["user_code"] = user[3]
        session["role"] = user[4]
        session["name"] = user[5]
        session["last_name"] = user[6]
        session["study_area"] = user[7]
        session["study_speciality"] = user[8]
        session["term"] = user[9]
        
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (user[0],))
            conn.commit()
            cur.close()
            conn.close()
        
        redirect_url = "/admin-dashboard" if user[4] == "admin" else "/student-dashboard"
        
        return jsonify({
            "success": True,
            "message": "Inicio de sesión exitoso",
            "user": {
                "id": user[0],
                "email": user[1],
                "role": user[4],
                "name": user[5],
                "last_name": user[6]
            },
            "redirect": redirect_url
        }), 200
        
    except Exception as e:
        print(f"Error en login: {e}")
        return jsonify({
            "success": False,
            "message": "Error interno del servidor"
        }), 500

@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada exitosamente", "info")
    return redirect(url_for("auth"))

@app.route("/profile")
def profile():
    if "user_id" not in session:
        flash("Debes iniciar sesión para acceder a tu perfil", "warning")
        return redirect(url_for("auth"))
    
    return render_template("profile.html")

@app.route("/post")
def post():
    if "user_id" not in session:
        flash("Debes iniciar sesión para crear una queja", "warning")
        return redirect(url_for("auth"))
    
    return render_template("post.html")

@app.route("/student-dashboard")
def student_dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth"))
    
    if session.get("role") != "student":
        flash("Acceso no autorizado", "error")
        return redirect(url_for("auth"))
    
    return render_template("index.html")

@app.route("/admin-dashboard")
def admin_dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth"))
    
    if session.get("role") != "admin":
        flash("Acceso no autorizado", "error")
        return redirect(url_for("auth"))
    
    return render_template("admin_dashboard.html")

@app.route("/check-session")
def check_session():
    if "user_id" in session:
        return jsonify({
            "authenticated": True,
            "user": {
                "id": session["user_id"],
                "email": session["email"],
                "name": session["name"],
                "role": session["role"]
            }
        })
    return jsonify({"authenticated": False})

@app.context_processor
def inject_user():
    if "user_id" in session:
        return {
            "current_user": {
                "id": session["user_id"],
                "email": session["email"],
                "name": session["name"],
                "last_name": session["last_name"],
                "role": session["role"],
                "study_area": session.get("study_area"),
                "term": session.get("term"),
                "initials": f"{session['name'][0]}{session['last_name'][0]}".upper()
            },
            "is_authenticated": True
        }
    return {"current_user": None, "is_authenticated": False}

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500

def create_app():
    return app
