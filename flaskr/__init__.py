from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
import mariadb

def get_db_connection():
    try:
        conn = mariadb.connect(
            user="user",
            password="123",
            host="127.0.0.1",
            port=3306,
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
        
        redirect_url = "/" if user[4] == "admin" else "/student-dashboard"
        
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

# ====== NUEVOS ENDPOINTS PARA MANEJO DINÁMICO DE TICKETS ======

@app.route('/api/tickets')
def get_tickets():
    """Endpoint para obtener todos los tickets dinámicamente"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    
    try:
        cur = conn.cursor()
        
        # Query para obtener tickets con información del usuario
        query = """
            SELECT 
                c.id,
                c.complaint_type,
                c.category,
                c.priority,
                c.subject,
                c.description,
                c.incident_date,
                c.status,
                c.created_at,
                u.name,
                u.last_name,
                u.avatar_initials
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.is_active = TRUE
            ORDER BY c.created_at DESC
        """
        
        cur.execute(query)
        results = cur.fetchall()
        
        # Mapeo de categorías para mostrar nombres amigables
        category_names = {
            'servicios-academicos': 'Servicios Académicos',
            'infraestructura': 'Infraestructura',
            'servicios-estudiantiles': 'Servicios Estudiantiles',
            'tecnologia': 'Tecnología',
            'administrativo': 'Administrativo',
            'biblioteca': 'Biblioteca',
            'cafeteria': 'Cafetería',
            'otro': 'Otro'
        }
        
        tickets = []
        for row in results:
            ticket = {
                'id': row[0],
                'complaint_type': row[1],
                'category': row[2],
                'categoryName': category_names.get(row[2], row[2].title()),
                'priority': row[3],
                'title': row[4],
                'content': row[5],
                'incident_date': row[6].strftime('%Y-%m-%d') if row[6] else None,
                'status': row[7],
                'date': row[8].strftime('%Y-%m-%d'),
                'created_at': row[8].strftime('%Y-%m-%d %H:%M:%S'),
                'user': {
                    'name': row[9],
                    'last_name': row[10],
                    'initials': row[11] if row[11] else f"{row[9][0]}{row[10][0]}".upper()
                }
            }
            tickets.append(ticket)
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'tickets': tickets,
            'total': len(tickets)
        })
        
    except mariadb.Error as e:
        print(f"Error fetching tickets: {e}")
        if conn:
            conn.close()
        return jsonify({'error': 'Error al obtener los tickets'}), 500

@app.route('/api/tickets/filter/<category>')
def get_tickets_by_category(category):
    """Endpoint para filtrar tickets por categoría"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    
    try:
        cur = conn.cursor()
        
        # Si la categoría es 'todos', obtener todos los tickets
        if category == 'todos':
            return get_tickets()
        
        query = """
            SELECT 
                c.id,
                c.complaint_type,
                c.category,
                c.priority,
                c.subject,
                c.description,
                c.incident_date,
                c.status,
                c.created_at,
                u.name,
                u.last_name,
                u.avatar_initials
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.is_active = TRUE AND c.category = ?
            ORDER BY c.created_at DESC
        """
        
        cur.execute(query, (category,))
        results = cur.fetchall()
        
        category_names = {
            'servicios-academicos': 'Servicios Académicos',
            'infraestructura': 'Infraestructura',
            'servicios-estudiantiles': 'Servicios Estudiantiles',
            'tecnologia': 'Tecnología',
            'administrativo': 'Administrativo',
            'biblioteca': 'Biblioteca',
            'cafeteria': 'Cafetería',
            'otro': 'Otro'
        }
        
        tickets = []
        for row in results:
            ticket = {
                'id': row[0],
                'complaint_type': row[1],
                'category': row[2],
                'categoryName': category_names.get(row[2], row[2].title()),
                'priority': row[3],
                'title': row[4],
                'content': row[5],
                'incident_date': row[6].strftime('%Y-%m-%d') if row[6] else None,
                'status': row[7],
                'date': row[8].strftime('%Y-%m-%d'),
                'created_at': row[8].strftime('%Y-%m-%d %H:%M:%S'),
                'user': {
                    'name': row[9],
                    'last_name': row[10],
                    'initials': row[11] if row[11] else f"{row[9][0]}{row[10][0]}".upper()
                }
            }
            tickets.append(ticket)
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'tickets': tickets,
            'total': len(tickets),
            'category': category
        })
        
    except mariadb.Error as e:
        print(f"Error filtering tickets: {e}")
        if conn:
            conn.close()
        return jsonify({'error': 'Error al filtrar los tickets'}), 500

@app.route('/api/tickets/stats')
def get_tickets_stats():
    """Endpoint para obtener estadísticas de tickets"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    
    try:
        cur = conn.cursor()
        
        # Estadísticas por estado
        status_query = """
            SELECT status, COUNT(*) as count
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.is_active = TRUE
            GROUP BY status
        """
        
        cur.execute(status_query)
        status_results = cur.fetchall()
        
        # Estadísticas por categoría
        category_query = """
            SELECT category, COUNT(*) as count
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.is_active = TRUE
            GROUP BY category
        """
        
        cur.execute(category_query)
        category_results = cur.fetchall()
        
        # Total de tickets
        total_query = """
            SELECT COUNT(*) as total
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.is_active = TRUE
        """
        
        cur.execute(total_query)
        total_result = cur.fetchone()
        
        # Estadísticas por prioridad
        priority_query = """
            SELECT priority, COUNT(*) as count
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.is_active = TRUE
            GROUP BY priority
        """
        
        cur.execute(priority_query)
        priority_results = cur.fetchall()
        
        cur.close()
        conn.close()
        
        stats = {
            'total_tickets': total_result[0],
            'by_status': {row[0]: row[1] for row in status_results},
            'by_category': {row[0]: row[1] for row in category_results},
            'by_priority': {row[0]: row[1] for row in priority_results}
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except mariadb.Error as e:
        print(f"Error getting stats: {e}")
        if conn:
            conn.close()
        return jsonify({'error': 'Error al obtener estadísticas'}), 500

@app.route('/api/tickets/user/<int:user_id>')
def get_user_tickets(user_id):
    """Endpoint para obtener tickets de un usuario específico"""
    # Verificar autenticación
    if "user_id" not in session:
        return jsonify({'error': 'No autenticado'}), 401
    
    # Solo permitir ver sus propios tickets o si es admin
    if session["user_id"] != user_id and session.get("role") != "admin":
        return jsonify({'error': 'No autorizado'}), 403
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    
    try:
        cur = conn.cursor()
        
        query = """
            SELECT 
                c.id,
                c.complaint_type,
                c.category,
                c.priority,
                c.subject,
                c.description,
                c.incident_date,
                c.status,
                c.created_at,
                u.name,
                u.last_name,
                u.avatar_initials
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            WHERE c.user_id = ? AND u.is_active = TRUE
            ORDER BY c.created_at DESC
        """
        
        cur.execute(query, (user_id,))
        results = cur.fetchall()
        
        category_names = {
            'servicios-academicos': 'Servicios Académicos',
            'infraestructura': 'Infraestructura',
            'servicios-estudiantiles': 'Servicios Estudiantiles',
            'tecnologia': 'Tecnología',
            'administrativo': 'Administrativo',
            'biblioteca': 'Biblioteca',
            'cafeteria': 'Cafetería',
            'otro': 'Otro'
        }
        
        tickets = []
        for row in results:
            ticket = {
                'id': row[0],
                'complaint_type': row[1],
                'category': row[2],
                'categoryName': category_names.get(row[2], row[2].title()),
                'priority': row[3],
                'title': row[4],
                'content': row[5],
                'incident_date': row[6].strftime('%Y-%m-%d') if row[6] else None,
                'status': row[7],
                'date': row[8].strftime('%Y-%m-%d'),
                'created_at': row[8].strftime('%Y-%m-%d %H:%M:%S'),
                'user': {
                    'name': row[9],
                    'last_name': row[10],
                    'initials': row[11] if row[11] else f"{row[9][0]}{row[10][0]}".upper()
                }
            }
            tickets.append(ticket)
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'tickets': tickets,
            'total': len(tickets),
            'user_id': user_id
        })
        
    except mariadb.Error as e:
        print(f"Error getting user tickets: {e}")
        if conn:
            conn.close()
        return jsonify({'error': 'Error al obtener tickets del usuario'}), 500

@app.route('/api/tickets/<int:ticket_id>/status', methods=['PUT'])
def update_ticket_status(ticket_id):
    """Endpoint para actualizar el estado de un ticket (solo admin)"""
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        new_status = data.get('status', '').strip()
        
        if new_status not in ['pendiente', 'en-proceso', 'resuelto', 'escalado']:
            return jsonify({'error': 'Estado no válido'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
        cur = conn.cursor()
        
        # Actualizar el estado del ticket
        cur.execute("""
            UPDATE complaints 
            SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (new_status, ticket_id))
        
        if cur.rowcount == 0:
            cur.close()
            conn.close()
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Estado actualizado correctamente',
            'ticket_id': ticket_id,
            'new_status': new_status
        })
        
    except Exception as e:
        print(f"Error updating ticket status: {e}")
        return jsonify({'error': 'Error al actualizar el estado'}), 500

# ====== FIN DE NUEVOS ENDPOINTS ======

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        flash("Debes iniciar sesión para acceder a tu perfil", "warning")
        return redirect(url_for("auth"))

    user_id = session["user_id"]
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Error de conexión con base de datos"}), 500
    cur = conn.cursor()

    if request.method == "POST":
        data = request.get_json()
        name = data.get("name", "").strip()
        last_name = data.get("last_name", "").strip()
        email = data.get("email", "").strip().lower()
        study_area = data.get("study_area", "").strip()
        study_speciality = data.get("study_speciality", "").strip()
        term = data.get("term", 1)
        personal_description = data.get("personal_description", "").strip()
        initials = f"{name[0]}{last_name[0]}".upper() if name and last_name else ""

        try:
            cur.execute("""
                UPDATE users SET
                    name = ?, last_name = ?, email = ?, 
                    study_area = ?, study_speciality = ?, 
                    term = ?, personal_description = ?, 
                    avatar_initials = ?
                WHERE id = ?
            """, (name, last_name, email, study_area, study_speciality, term, personal_description, initials, user_id))
            conn.commit()
            cur.close()
            conn.close()

            session["name"] = name
            session["last_name"] = last_name
            session["email"] = email
            session["study_area"] = study_area
            session["study_speciality"] = study_speciality
            session["term"] = term

            return jsonify({"success": True, "message": "Perfil actualizado correctamente"})
        except mariadb.Error as e:
            return jsonify({"success": False, "message": f"Error al actualizar: {e}"})

    cur.execute("SELECT name, last_name, email, study_area, study_speciality, term, personal_description FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    user_data = {
        "name": row[0],
        "last_name": row[1],
        "email": row[2],
        "study_area": row[3],
        "study_speciality": row[4],
        "term": row[5],
        "personal_description": row[6],
        "initials": f"{row[0][0]}{row[1][0]}".upper() if row[0] and row[1] else ""
    }

    return render_template("profile.html", user=user_data)

@app.route("/post", methods=["GET", "POST"])
def post():
    if "user_id" not in session:
        flash("Debes iniciar sesión para crear una queja", "warning")
        return redirect(url_for("auth"))
    
    if request.method == "POST":
        try:
            data = request.get_json() if request.is_json else request.form
            
            complaint_type = data.get("type", "").strip()
            category = data.get("category", "").strip()
            priority = data.get("priority", "").strip()
            subject = data.get("subject", "").strip()
            description = data.get("description", "").strip()
            incident_date = data.get("incident_date")

            errors = []
            if not complaint_type:
                errors.append("El tipo de solicitud es requerido")
            if not category:
                errors.append("La categoría es requerida")
            if not priority:
                errors.append("La prioridad es requerida")
            if not subject or len(subject) < 5:
                errors.append("El asunto es requerido (mínimo 5 caracteres)")
            if not description or len(description) < 20:
                errors.append("La descripción es requerida (mínimo 20 caracteres)")
            
            if errors:
                return jsonify({
                    "success": False,
                    "message": "Errores de validación",
                    "errors": errors
                }), 400
            
            conn = get_db_connection()
            if not conn:
                return jsonify({
                    "success": False,
                    "message": "Error de conexión a la base de datos"
                }), 500
            
            try:
                cur = conn.cursor()
                query = """
                    INSERT INTO complaints (
                        user_id, complaint_type, category, priority, 
                        subject, description, incident_date, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pendiente')
                """
                
                cur.execute(query, (
                    session["user_id"],
                    complaint_type,
                    category,
                    priority,
                    subject,
                    description,
                    incident_date if incident_date else None
                ))
                
                conn.commit()
                complaint_id = cur.lastrowid
                cur.close()
                conn.close()
                
                return jsonify({
                    "success": True,
                    "message": "¡Solicitud enviada correctamente! Te contactaremos pronto.",
                    "complaint_id": complaint_id
                }), 201
                
            except mariadb.Error as e:
                print(f"Error al crear queja: {e}")
                return jsonify({
                    "success": False,
                    "message": "Error al guardar la solicitud"
                }), 500
                
        except Exception as e:
            print(f"Error en post: {e}")
            return jsonify({
                "success": False,
                "message": "Error interno del servidor"
            }), 500
    
    user_data = {
        "full_name": f"{session['name']} {session['last_name']}",
        "email": session['email'],
        "study_area": session.get("study_area", ""),
        "term": session.get("term", "")
    }
    
    return render_template("post.html", user=user_data)

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

@app.route("/ticket")
def ticket_validation():
    """Página para validar tickets - solo admin"""
    if "user_id" not in session:
        return redirect(url_for("auth"))
    
    if session.get("role") != "admin":
        flash("Acceso no autorizado", "error")
        return redirect(url_for("auth"))
    
    return render_template("ticket.html")


@app.route("/ticket/<int:ticket_id>")
def ticket_detail(ticket_id):
    """Página de detalle de ticket para resolución - solo admin"""
    if "user_id" not in session:
        return redirect(url_for("auth"))
    
    if session.get("role") != "admin":
        flash("Acceso no autorizado", "error")
        return redirect(url_for("auth"))
    
    conn = get_db_connection()
    if not conn:
        flash("Error de conexión a la base de datos", "error")
        return redirect(url_for("ticket_validation"))
    
    try:
        cur = conn.cursor()
        
        # Cambiado a %s para MariaDB
        query = """
            SELECT 
                c.id, c.complaint_type, c.category, c.priority, c.subject, 
                c.description, c.incident_date, c.status, c.created_at,
                u.name, u.last_name, u.email, u.study_area, u.term,
                cr.assigned_to, cr.admin_response, cr.resolution_date,
                cr.time_spent, cr.follow_up_required, cr.follow_up_date,
                cr.internal_notes
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            LEFT JOIN complaint_responses cr ON c.id = cr.complaint_id
            WHERE c.id = %s AND u.is_active = TRUE
        """
        
        cur.execute(query, (ticket_id,))
        result = cur.fetchone()
        
        if not result:
            flash("Ticket no encontrado", "error")
            return redirect(url_for("ticket_validation"))
        
        category_names = {
            'servicios-academicos': 'Servicios Académicos',
            'infraestructura': 'Infraestructura',
            'servicios-estudiantiles': 'Servicios Estudiantiles',
            'tecnologia': 'Tecnología',
            'administrativo': 'Administrativo',
            'biblioteca': 'Biblioteca',
            'cafeteria': 'Cafetería',
            'otro': 'Otro'
        }
        
        ticket_data = {
            'id': result[0],
            'complaint_type': result[1],
            'category': result[2],
            'categoryName': category_names.get(result[2], result[2].title()),
            'priority': result[3],
            'subject': result[4],
            'description': result[5],
            'incident_date': result[6].strftime('%Y-%m-%d') if result[6] else None,
            'status': result[7],
            'created_at': result[8].strftime('%Y-%m-%d') if result[8] else None,
            'user': {
                'name': result[9],
                'last_name': result[10],
                'email': result[11],
                'study_area': result[12],
                'term': result[13]
            },
            'response': {
                'assigned_to': result[14],
                'admin_response': result[15],
                'resolution_date': result[16].strftime('%Y-%m-%d') if result[16] else None,
                'time_spent': float(result[17]) if result[17] else None,
                'follow_up_required': result[18],
                'follow_up_date': result[19].strftime('%Y-%m-%d') if result[19] else None,
                'internal_notes': result[20]
            }
        }
        
        cur.close()
        conn.close()
        
        return render_template("ticket_resolution.html", ticket=ticket_data)
        
    except mariadb.Error as e:
        print(f"Error getting ticket detail: {e}")
        flash("Error al obtener los datos del ticket", "error")
        return redirect(url_for("ticket_validation"))

@app.route("/api/tickets/<int:ticket_id>")
def api_ticket_detail(ticket_id):
    """Endpoint API para obtener detalles del ticket"""
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    if not conn:
        flash("Error de conexión a la base de datos", "error")
        return redirect(url_for("ticket_validation"))
    
    try:
        cur = conn.cursor()
        query = """
            SELECT 
                c.id, c.complaint_type, c.category, c.priority, c.subject, 
                c.description, c.incident_date, c.status, c.created_at,
                u.name, u.last_name, u.email, u.study_area, u.term,
                cr.assigned_to, cr.admin_response, cr.resolution_date,
                cr.time_spent, cr.follow_up_required, cr.follow_up_date,
                cr.internal_notes
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            LEFT JOIN complaint_responses cr ON c.id = cr.complaint_id
            WHERE c.id = %s AND u.is_active = TRUE
        """
        
        cur.execute(query, (ticket_id,))
        result = cur.fetchone()
        
        if not result:
            return jsonify({"success": False, "message": "Ticket not found"}), 404
        
        category_names = {
            'servicios-academicos': 'Servicios Académicos',
            'infraestructura': 'Infraestructura',
            'servicios-estudiantiles': 'Servicios Estudiantiles',
            'tecnologia': 'Tecnología',
            'administrativo': 'Administrativo',
            'biblioteca': 'Biblioteca',
            'cafeteria': 'Cafetería',
            'otro': 'Otro'
        }
        
        ticket_data = {
            'success': True,
            'ticket': {
                'id': result[0],
                'complaint_type': result[1],
                'category': result[2],
                'categoryName': category_names.get(result[2], result[2].title()),
                'priority': result[3],
                'subject': result[4],
                'description': result[5],
                'incident_date': result[6].strftime('%Y-%m-%d') if result[6] else None,
                'status': result[7],
                'created_at': result[8].strftime('%Y-%m-%d') if result[8] else None,
                'user': {
                    'name': result[9],
                    'last_name': result[10],
                    'email': result[11],
                    'study_area': result[12],
                    'term': result[13]
                },
                'response': {
                    'assigned_to': result[14],
                    'admin_response': result[15],
                    'resolution_date': result[16].strftime('%Y-%m-%d') if result[16] else None,
                    'time_spent': float(result[17]) if result[17] else None,
                    'follow_up_required': result[18],
                    'follow_up_date': result[19].strftime('%Y-%m-%d') if result[19] else None,
                    'internal_notes': result[20]
                }
            }
        }
        
        return jsonify(ticket_data)
        
    except mariadb.Error as e:
        print(f"API Error getting ticket detail: {e}")
        return jsonify({"success": False, "message": "Database error"}), 500
    finally:
        if 'cur' in locals(): cur.close()
        if conn: conn.close()

@app.route("/api/tickets/<int:ticket_id>/resolve", methods=["POST"])
def resolve_ticket(ticket_id):
    """Endpoint para resolver un ticket"""
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400
    
    required_fields = ['assigned_to', 'admin_response', 'status', 'resolution_date']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"success": False, "message": f"Missing required field: {field}"}), 400
    
    # Validar y formatear time_spent
    time_spent = data.get('time_spent')
    if time_spent == '' or time_spent is None:
        time_spent = None  # Permitir NULL en la base de datos
    else:
        try:
            time_spent = float(time_spent)
            if time_spent < 0 or time_spent > 99.99:  # DECIMAL(4,2) permite hasta 99.99
                return jsonify({"success": False, "message": "El tiempo invertido debe estar entre 0 y 99.99 horas"}), 400
        except ValueError:
            return jsonify({"success": False, "message": "El tiempo invertido debe ser un número válido"}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database error"}), 500
    
    try:
        cur = conn.cursor()
        
        # 1. Actualizar el estado del ticket en la tabla complaints
        update_complaint = """
            UPDATE complaints 
            SET status = %s 
            WHERE id = %s
        """
        cur.execute(update_complaint, (data['status'], ticket_id))
        
        # 2. Insertar o actualizar la respuesta en complaint_responses
        cur.execute("SELECT id FROM complaint_responses WHERE complaint_id = %s", (ticket_id,))
        existing_response = cur.fetchone()
        
        if existing_response:
            update_response = """
                UPDATE complaint_responses 
                SET assigned_to = %s, 
                    admin_response = %s, 
                    resolution_date = %s, 
                    time_spent = %s, 
                    follow_up_required = %s, 
                    follow_up_date = %s, 
                    internal_notes = %s 
                WHERE complaint_id = %s
            """
            cur.execute(update_response, (
                data['assigned_to'],
                data['admin_response'],
                data['resolution_date'],
                time_spent,
                data.get('follow_up_required', False),
                data.get('follow_up_date'),
                data.get('internal_notes'),
                ticket_id
            ))
        else:
            insert_response = """
                INSERT INTO complaint_responses (
                    complaint_id, assigned_to, admin_response, 
                    resolution_date, time_spent, follow_up_required, 
                    follow_up_date, internal_notes
                ) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(insert_response, (
                ticket_id,
                data['assigned_to'],
                data['admin_response'],
                data['resolution_date'],
                time_spent,
                data.get('follow_up_required', False),
                data.get('follow_up_date'),
                data.get('internal_notes')
            ))
        
        conn.commit()
        return jsonify({"success": True, "message": "Ticket resuelto exitosamente"})
        
    except mariadb.Error as e:
        conn.rollback()
        print(f"Error resolving ticket: {e}")
        return jsonify({"success": False, "message": "Database error"}), 500
    finally:
        if 'cur' in locals(): cur.close()
        if conn: conn.close()

@app.route('/api/tickets/<int:ticket_id>')
def get_ticket_details(ticket_id):
    """Endpoint para obtener detalles de un ticket específico"""
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({'error': 'No autorizado'}), 403
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    
    try:
        cur = conn.cursor()
        
        # Query para obtener el ticket con información del usuario
        query = """
            SELECT 
                c.id, c.complaint_type, c.category, c.priority, c.subject, 
                c.description, c.incident_date, c.status, c.created_at,
                u.name, u.last_name, u.email, u.study_area, u.term,
                cr.assigned_to, cr.admin_response, cr.resolution_date,
                cr.time_spent, cr.follow_up_required, cr.follow_up_date,
                cr.internal_notes
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            LEFT JOIN complaint_responses cr ON c.id = cr.complaint_id
            WHERE c.id = ? AND u.is_active = TRUE
        """
        
        cur.execute(query, (ticket_id,))
        result = cur.fetchone()
        
        if not result:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        # Mapeo de categorías para mostrar nombres amigables
        category_names = {
            'servicios-academicos': 'Servicios Académicos',
            'infraestructura': 'Infraestructura',
            'servicios-estudiantiles': 'Servicios Estudiantiles',
            'tecnologia': 'Tecnología',
            'administrativo': 'Administrativo',
            'biblioteca': 'Biblioteca',
            'cafeteria': 'Cafetería',
            'otro': 'Otro'
        }
        
        ticket_data = {
            'id': result[0],
            'complaint_type': result[1],
            'category': result[2],
            'categoryName': category_names.get(result[2], result[2].title()),
            'priority': result[3],
            'subject': result[4],
            'description': result[5],
            'incident_date': result[6].strftime('%Y-%m-%d') if result[6] else None,
            'status': result[7],
            'created_at': result[8].strftime('%Y-%m-%d %H:%M:%S'),
            'user': {
                'name': result[9],
                'last_name': result[10],
                'email': result[11],
                'study_area': result[12],
                'term': result[13]
            },
            'response': {
                'assigned_to': result[14],
                'admin_response': result[15],
                'resolution_date': result[16].strftime('%Y-%m-%d') if result[16] else None,
                'time_spent': float(result[17]) if result[17] else None,
                'follow_up_required': bool(result[18]),
                'follow_up_date': result[19].strftime('%Y-%m-%d') if result[19] else None,
                'internal_notes': result[20]
            }
        }
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'ticket': ticket_data
        })
        
    except mariadb.Error as e:
        print(f"Error getting ticket details: {e}")
        if conn:
            conn.close()
        return jsonify({'error': 'Error al obtener los detalles del ticket'}), 500

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
