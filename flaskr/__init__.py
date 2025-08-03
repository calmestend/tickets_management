import time
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
import mariadb
import os
from werkzeug.utils import secure_filename
from PIL import Image

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
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB máximo

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
        
        redirect_url = "/"
        
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

# ========== TICKETS ==========

@app.route('/api/tickets')
def get_tickets():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    try:
        cur = conn.cursor()
        # Obtener datos básicos del ticket
        query = """
            SELECT c.id, c.complaint_type, c.category, c.subject, c.description, c.incident_date,
                   c.status, c.created_at, u.name, u.last_name, u.avatar_initials
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.is_active = TRUE
            ORDER BY c.created_at DESC
        """
        cur.execute(query)
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
            ticket_id = row[0]
            # Imagen del usuario: primer archivo imagen de complaint_attachments
            cur.execute("""
                SELECT file_path FROM complaint_attachments 
                WHERE complaint_id = ? AND file_type IN ('jpg','jpeg','png','gif')
                ORDER BY id ASC LIMIT 1
            """, (ticket_id,))
            user_img_row = cur.fetchone()
            user_image = user_img_row[0] if user_img_row else ""

            # Imagen del admin: primer archivo imagen de resolution_images
            cur.execute("""
                SELECT file_path FROM resolution_images
                WHERE complaint_id = ? AND file_type IN ('jpg','jpeg','png','gif')
                ORDER BY id ASC LIMIT 1
            """, (ticket_id,))
            admin_img_row = cur.fetchone()
            admin_image = admin_img_row[0] if admin_img_row else ""

            ticket = {
                'id': ticket_id,
                'complaint_type': row[1],
                'category': row[2],
                'categoryName': category_names.get(row[2], row[2].title()),
                'title': row[3],
                'content': row[4],
                'incident_date': row[5].strftime('%Y-%m-%d') if row[5] else None,
                'status': row[6],
                'date': row[7].strftime('%Y-%m-%d'),
                'created_at': row[7].strftime('%Y-%m-%d %H:%M:%S'),
                'user': {
                    'name': row[8],
                    'last_name': row[9],
                    'initials': row[10] if row[10] else f"{row[8][0]}{row[9][0]}".upper()
                },
                'user_image': user_image,
                'admin_image': admin_image,
                'priority': 'media' # Si tienes prioridad, cámbialo
            }
            tickets.append(ticket)
        cur.close()
        conn.close()
        return jsonify({'success': True, 'tickets': tickets, 'total': len(tickets)})
    except mariadb.Error as e:
        print(f"Error fetching tickets: {e}")
        if conn:
            conn.close()
        return jsonify({'error': 'Error al obtener los tickets'}), 500

@app.route('/api/tickets/filter/<category>')
def get_tickets_by_category(category):
    if category == 'todos':
        return get_tickets()
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    try:
        cur = conn.cursor()
        query = """
            SELECT c.id, c.complaint_type, c.category, c.subject, c.description, c.incident_date,
                   c.status, c.created_at, u.name, u.last_name, u.avatar_initials
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
            ticket_id = row[0]
            cur.execute("""
                SELECT file_path FROM complaint_attachments 
                WHERE complaint_id = ? AND file_type IN ('jpg','jpeg','png','gif')
                ORDER BY id ASC LIMIT 1
            """, (ticket_id,))
            user_img_row = cur.fetchone()
            user_image = user_img_row[0] if user_img_row else ""

            cur.execute("""
                SELECT file_path FROM resolution_images
                WHERE complaint_id = ? AND file_type IN ('jpg','jpeg','png','gif')
                ORDER BY id ASC LIMIT 1
            """, (ticket_id,))
            admin_img_row = cur.fetchone()
            admin_image = admin_img_row[0] if admin_img_row else ""

            ticket = {
                'id': ticket_id,
                'complaint_type': row[1],
                'category': row[2],
                'categoryName': category_names.get(row[2], row[2].title()),
                'title': row[3],
                'content': row[4],
                'incident_date': row[5].strftime('%Y-%m-%d') if row[5] else None,
                'status': row[6],
                'date': row[7].strftime('%Y-%m-%d'),
                'created_at': row[7].strftime('%Y-%m-%d %H:%M:%S'),
                'user': {
                    'name': row[8],
                    'last_name': row[9],
                    'initials': row[10] if row[10] else f"{row[8][0]}{row[9][0]}".upper()
                },
                'user_image': user_image,
                'admin_image': admin_image,
                'priority': 'media'
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
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    try:
        cur = conn.cursor()
        status_query = """
            SELECT status, COUNT(*) as count
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.is_active = TRUE
            GROUP BY status
        """
        cur.execute(status_query)
        status_results = cur.fetchall()
        category_query = """
            SELECT category, COUNT(*) as count
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.is_active = TRUE
            GROUP BY category
        """
        cur.execute(category_query)
        category_results = cur.fetchall()
        total_query = """
            SELECT COUNT(*) as total
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            WHERE u.is_active = TRUE
        """
        cur.execute(total_query)
        total_result = cur.fetchone()
        cur.close()
        conn.close()
        stats = {
            'total_tickets': total_result[0],
            'by_status': {row[0]: row[1] for row in status_results},
            'by_category': {row[0]: row[1] for row in category_results},
        }
        return jsonify({'success': True, 'stats': stats})
    except mariadb.Error as e:
        print(f"Error getting stats: {e}")
        if conn:
            conn.close()
        return jsonify({'error': 'Error al obtener estadísticas'}), 500

@app.route('/api/tickets/user/<int:user_id>')
def get_user_tickets(user_id):
    if "user_id" not in session:
        return jsonify({'error': 'No autenticado'}), 401
    if session["user_id"] != user_id and session.get("role") != "admin":
        return jsonify({'error': 'No autorizado'}), 403
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    try:
        cur = conn.cursor()
        query = """
            SELECT c.id, c.complaint_type, c.category, c.subject, c.description, c.incident_date,
                   c.status, c.created_at, u.name, u.last_name, u.avatar_initials
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
                'title': row[3],
                'content': row[4],
                'incident_date': row[5].strftime('%Y-%m-%d') if row[5] else None,
                'status': row[6],
                'date': row[7].strftime('%Y-%m-%d'),
                'created_at': row[7].strftime('%Y-%m-%d %H:%M:%S'),
                'user': {
                    'name': row[8],
                    'last_name': row[9],
                    'initials': row[10] if row[10] else f"{row[8][0]}{row[9][0]}".upper()
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
        cur.execute("UPDATE complaints SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, ticket_id))
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

@app.route("/api/tickets/<int:ticket_id>/resolve", methods=["POST"])
def resolve_ticket(ticket_id):
    """
    Endpoint para resolver un ticket, permitiendo guardar imagen de comprobante.
    """
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    # Procesar datos de formulario (soporta FormData)
    form = request.form
    files = request.files
    assigned_to = form.get("assigned_to", "").strip()
    admin_response = form.get("admin_response", "").strip()
    status = form.get("status", "").strip()
    resolution_date = form.get("resolution_date", "").strip()
    time_spent = form.get("time_spent", "")
    proof_image = files.get("proof_image")

    # Validaciones
    required_fields = [assigned_to, admin_response, status, resolution_date]
    if not all(required_fields):
        return jsonify({"success": False, "message": "Completa todos los campos requeridos"}), 400

    try:
        time_spent = float(time_spent) if time_spent not in ("", None) else None
        if time_spent is not None and (time_spent < 0 or time_spent > 99.99):
            return jsonify({"success": False, "message": "El tiempo invertido debe estar entre 0 y 99.99 horas"}), 400
    except ValueError:
        return jsonify({"success": False, "message": "El tiempo invertido debe ser un número válido"}), 400

    # Procesar imagen de comprobante
    proof_info = None
    if proof_image and proof_image.filename:
        allowed_extensions = {"jpg", "jpeg", "png", "gif"}
        allowed_mime_types = {"image/jpeg", "image/jpg", "image/png", "image/gif"}
        filename = secure_filename(proof_image.filename)
        file_ext = filename.rsplit(".", 1)[-1].lower()
        if file_ext not in allowed_extensions or proof_image.content_type not in allowed_mime_types:
            return jsonify({"success": False, "message": "Formato de imagen no permitido: JPG, JPEG, PNG, GIF"}), 400
        proof_image.seek(0, os.SEEK_END)
        file_size = proof_image.tell()
        proof_image.seek(0)
        if file_size > 5 * 1024 * 1024:
            return jsonify({"success": False, "message": "La imagen de comprobante debe ser menor a 5MB"}), 400

        # Guardar imagen
        upload_dir = os.path.join(app.static_folder or os.path.dirname(os.path.abspath(__file__)), "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        user_email = session["email"].split("@")[0]
        user_id = session["user_id"]
        timestamp = int(time.time())
        unique_filename = f"resolution_{user_email}_{user_id}_{ticket_id}_{timestamp}.{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        proof_image.save(file_path)

        # Opcional: procesar imagen
        try:
            with Image.open(file_path) as img:
                max_width, max_height = 1920, 1080
                if img.width > max_width or img.height > max_height:
                    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                img.save(file_path)
        except Exception as e:
            print(f"Procesamiento de imagen fallido: {e}")

        proof_info = {
            "saved_name": unique_filename,
            "file_path": f"uploads/{unique_filename}",
            "file_type": file_ext,
            "file_size": file_size
        }

    # Guardar resolución en la base de datos
    conn = get_db_connection()
    if not conn:
        # Eliminar imagen si no se pudo conectar a BD
        if proof_info and os.path.exists(os.path.join(app.static_folder, proof_info["file_path"])):
            os.remove(os.path.join(app.static_folder, proof_info["file_path"]))
        return jsonify({"success": False, "message": "Error de conexión a la base de datos"}), 500

    try:
        cur = conn.cursor()
        cur.execute("UPDATE complaints SET status = ? WHERE id = ?", (status, ticket_id))
        cur.execute("SELECT id FROM complaint_responses WHERE complaint_id = ?", (ticket_id,))
        existing_response = cur.fetchone()

        # Crear tabla de imágenes de resolución si no existe
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resolution_images (
                id INT AUTO_INCREMENT PRIMARY KEY,
                complaint_id INT NOT NULL,
                saved_filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_type VARCHAR(10) NOT NULL,
                file_size INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
            );
        """)

        if existing_response:
            update_response = """
                UPDATE complaint_responses 
                SET assigned_to = ?, admin_response = ?, resolution_date = ?, time_spent = ?
                WHERE complaint_id = ?
            """
            cur.execute(update_response, (
                assigned_to,
                admin_response,
                resolution_date,
                time_spent,
                ticket_id
            ))
        else:
            insert_response = """
                INSERT INTO complaint_responses (
                    complaint_id, assigned_to, admin_response, resolution_date, time_spent
                ) VALUES (?, ?, ?, ?, ?)
            """
            cur.execute(insert_response, (
                ticket_id,
                assigned_to,
                admin_response,
                resolution_date,
                time_spent
            ))

        # Guardar la imagen de comprobante si existe
        if proof_info:
            insert_img = """
                INSERT INTO resolution_images (
                    complaint_id, saved_filename, file_path, file_type, file_size
                ) VALUES (?, ?, ?, ?, ?)
            """
            cur.execute(insert_img, (
                ticket_id,
                proof_info["saved_name"],
                proof_info["file_path"],
                proof_info["file_type"],
                proof_info["file_size"]
            ))

        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True, "message": "Ticket resuelto exitosamente"})
    except mariadb.Error as e:
        print(f"Error resolviendo ticket: {e}")
        if conn: conn.rollback()
        # Eliminar imagen si hay error de BD
        if proof_info and os.path.exists(os.path.join(app.static_folder, proof_info["file_path"])):
            os.remove(os.path.join(app.static_folder, proof_info["file_path"]))
        return jsonify({"success": False, "message": "Database error"}), 500
# ========== FIN DE TICKETS ==========

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
        print("="*50)
        print("INICIANDO PROCESAMIENTO POST")
        print("="*50)
        try:
            # Manejar datos del formulario
            data = request.form
            files = request.files.getlist('files')
            
            print(f"Datos recibidos: {dict(data)}")
            print(f"Archivos recibidos: {len(files)}")
            
            # Debug detallado de archivos sin consumir su contenido
            for i, file in enumerate(files):
                # Guardar posición actual
                current_pos = file.tell()
                
                # Obtener tamaño sin consumir contenido
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(current_pos)  # Volver a posición original
                
                print(f"Archivo {i}: nombre='{file.filename}', tipo='{file.content_type}', tamaño={file_size} bytes")

            complaint_type = data.get("complaint_type", "").strip()
            category = data.get("category", "").strip()
            subject = data.get("subject", "").strip()
            description = data.get("description", "").strip()
            incident_date = data.get("incident_date")

            # Validaciones
            errors = []
            if not complaint_type:
                errors.append("El tipo de solicitud es requerido")
            if not category:
                errors.append("La categoría es requerida")
            if not subject or len(subject) < 5:
                errors.append("El asunto es requerido (mínimo 5 caracteres)")
            if not description or len(description) < 20:
                errors.append("La descripción es requerida (mínimo 20 caracteres)")

            # Validar valores permitidos
            valid_types = ['queja', 'sugerencia', 'peticion']
            if complaint_type not in valid_types:
                errors.append("Tipo de solicitud no válido")

            valid_categories = [
                'servicios-academicos', 'infraestructura', 'servicios-estudiantiles',
                'tecnologia', 'administrativo', 'biblioteca', 'cafeteria', 'otro'
            ]
            if category not in valid_categories:
                errors.append("Categoría no válida")

            if errors:
                return jsonify({
                    "success": False,
                    "message": "Errores de validación",
                    "errors": errors
                }), 400

            # Procesar archivos adjuntos
            print("INICIANDO PROCESAMIENTO DE ARCHIVOS")
            uploaded_files = []
            if files and any(f.filename for f in files):  # Verificar que hay archivos válidos
                print(f"Hay archivos para procesar: {[f.filename for f in files if f.filename]}")
                
                # Crear directorio uploads de forma más robusta
                if app.static_folder:
                    upload_dir = os.path.join(app.static_folder, 'uploads')
                else:
                    # Fallback si static_folder no está configurado
                    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
                
                print(f"Directorio de destino: {upload_dir}")
                
                # Asegurarse de que el directorio existe
                try:
                    os.makedirs(upload_dir, exist_ok=True)
                    print(f"Directorio creado/verificado: {upload_dir}")
                    
                    # Verificar permisos de escritura
                    test_file = os.path.join(upload_dir, 'test_permission.txt')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    print("✓ Permisos de escritura verificados")
                except OSError as e:
                    print(f"ERROR CRÍTICO creando directorio: {e}")
                    return jsonify({
                        "success": False,
                        "message": f"Error configurando directorio de archivos: {str(e)}"
                    }), 500

                # Configuración actualizada para permitir más tipos de archivo
                max_files = 5
                max_file_size = 10 * 1024 * 1024  # 10MB
                
                # Extensiones permitidas actualizadas
                allowed_extensions = {
                    'jpg', 'jpeg', 'png', 'gif',  # Imágenes
                    'pdf',                        # PDFs
                    'doc', 'docx',               # Word
                    'txt'                        # Texto plano
                }
                
                # MIME types permitidos para validación adicional
                allowed_mime_types = {
                    'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
                    'application/pdf',
                    'application/msword',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'text/plain'
                }
                
                # Filtrar archivos vacíos
                valid_files = [f for f in files if f.filename and f.filename.strip()]
                
                if len(valid_files) > max_files:
                    return jsonify({
                        "success": False,
                        "message": f"Máximo {max_files} archivos permitidos"
                    }), 400

                for i, file in enumerate(valid_files):
                    print(f"\n--- PROCESANDO ARCHIVO {i+1}/{len(valid_files)} ---")
                    print(f"Nombre: {file.filename}")
                    print(f"Tipo MIME: {file.content_type}")
                    
                    # Validar nombre de archivo
                    if not file.filename:
                        print("Saltando archivo sin nombre")
                        continue
                        
                    filename = secure_filename(file.filename)
                    if not filename:
                        print("Saltando archivo con nombre inseguro")
                        continue
                    
                    print(f"Nombre seguro: {filename}")
                        
                    # Validar extensión
                    if '.' not in filename:
                        error_msg = f"Archivo sin extensión: {file.filename}"
                        print(f"ERROR: {error_msg}")
                        return jsonify({
                            "success": False,
                            "message": error_msg
                        }), 400
                        
                    file_ext = filename.rsplit('.', 1)[1].lower()
                    print(f"Extensión detectada: {file_ext}")
                    
                    # Validación dual: extensión Y tipo MIME
                    if file_ext not in allowed_extensions:
                        error_msg = f"Extensión de archivo no permitida: {filename}. Permitidas: {', '.join(sorted(allowed_extensions))}"
                        print(f"ERROR: {error_msg}")
                        return jsonify({
                            "success": False,
                            "message": error_msg
                        }), 400
                    
                    if file.content_type and file.content_type not in allowed_mime_types:
                        print(f"Advertencia: Tipo MIME no reconocido: {file.content_type} para archivo {filename}")
                        # No bloqueamos por MIME type, solo advertimos

                    # Validar tamaño del archivo
                    current_pos = file.tell()
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(current_pos)  # Volver a posición original
                    print(f"Tamaño del archivo: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")

                    if file_size == 0:
                        error_msg = f"Archivo vacío: {filename}"
                        print(f"ERROR: {error_msg}")
                        return jsonify({
                            "success": False,
                            "message": error_msg
                        }), 400

                    if file_size > max_file_size:
                        error_msg = f"Archivo muy grande: {filename} ({file_size / 1024 / 1024:.1f}MB). Máximo 10MB."
                        print(f"ERROR: {error_msg}")
                        return jsonify({
                            "success": False,
                            "message": error_msg
                        }), 400

                    # Generar nombre único
                    user_email = session['email'].split('@')[0]
                    user_db_id = session['user_id']  # ID de la BD
                    timestamp = int(time.time())  # Agregar timestamp para mayor unicidad
                    
                    # Mantener la extensión original
                    unique_filename = f"{user_email}_{user_db_id}_{timestamp}_{i+1}.{file_ext}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    
                    print(f"Nombre único generado: {unique_filename}")
                    print(f"Ruta completa: {file_path}")

                    try:
                        print("Intentando guardar archivo...")
                        # Guardar archivo
                        file.save(file_path)
                        print(f"✓ Archivo guardado exitosamente")
                        
                        # Verificar que realmente se guardó
                        if os.path.exists(file_path):
                            actual_size = os.path.getsize(file_path)
                            print(f"✓ Archivo verificado en disco, tamaño: {actual_size} bytes")
                            
                            # Verificar integridad del archivo
                            if actual_size != file_size:
                                print(f"Advertencia: Tamaño esperado {file_size} vs tamaño actual {actual_size}")
                        else:
                            raise Exception("El archivo no se encontró después de guardar")

                        # Solo procesar imágenes con PIL
                        if file_ext in ['jpg', 'jpeg', 'png', 'gif']:
                            print("Procesando como imagen...")
                            try:
                                # Procesar y optimizar imagen con PIL
                                with Image.open(file_path) as img:
                                    print(f"Imagen abierta: {img.size}, modo: {img.mode}")
                                    
                                    # Convertir a RGB si es necesario (para JPEGs)
                                    if file_ext in ['jpg', 'jpeg'] and img.mode in ('RGBA', 'P', 'L'):
                                        print("Convirtiendo imagen a RGB")
                                        img = img.convert('RGB')

                                    # Redimensionar si es muy grande
                                    max_width, max_height = 1920, 1080
                                    if img.width > max_width or img.height > max_height:
                                        original_size = img.size
                                        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                                        print(f"Imagen redimensionada de {original_size} a {img.size}")

                                    # Guardar imagen optimizada
                                    if file_ext in ['jpg', 'jpeg']:
                                        img.save(file_path, 'JPEG', quality=85, optimize=True)
                                    elif file_ext == 'png':
                                        img.save(file_path, 'PNG', optimize=True)
                                    elif file_ext == 'gif':
                                        img.save(file_path, 'GIF', optimize=True)
                                    
                                    print("✓ Imagen optimizada y guardada")
                            except Exception as img_error:
                                print(f"Advertencia procesando imagen {filename}: {str(img_error)}")
                                # Si falla el procesamiento de imagen, continuar con el archivo original
                                pass
                        else:
                            print("Archivo guardado sin procesamiento (no es imagen)")

                        # Actualizar tamaño después de procesamiento
                        final_size = os.path.getsize(file_path)
                        file_info = {
                            'original_name': file.filename,
                            'saved_name': unique_filename,
                            'path': f'uploads/{unique_filename}',
                            'size': final_size,
                            'type': file_ext
                        }
                        uploaded_files.append(file_info)
                        print(f"✓ Archivo agregado a la lista: {file_info}")

                    except Exception as e:
                        error_msg = f"Error procesando archivo {filename}: {str(e)}"
                        print(f"ERROR CRÍTICO: {error_msg}")
                        import traceback
                        traceback.print_exc()
                        
                        # Limpiar archivo temporal si existe
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                                print(f"Archivo temporal eliminado: {file_path}")
                            except:
                                print("Error eliminando archivo temporal")
                        
                        return jsonify({
                            "success": False,
                            "message": error_msg
                        }), 400
                        
                print(f"\n✓ PROCESAMIENTO DE ARCHIVOS COMPLETADO")
                print(f"Total archivos procesados: {len(uploaded_files)}")
            else:
                print("No hay archivos para procesar o todos están vacíos")

            # Conectar a la base de datos
            conn = get_db_connection()
            if not conn:
                # Limpiar archivos subidos si hay error de conexión
                cleanup_uploaded_files(uploaded_files)
                return jsonify({
                    "success": False,
                    "message": "Error de conexión a la base de datos"
                }), 500

            try:
                cur = conn.cursor()
                
                # Insertar queja principal
                query = """
                    INSERT INTO complaints (
                        user_id, complaint_type, category,
                        subject, description, incident_date, status
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pendiente')
                """

                cur.execute(query, (
                    session["user_id"],
                    complaint_type,
                    category,
                    subject,
                    description,
                    incident_date if incident_date and incident_date.strip() else None
                ))

                complaint_id = cur.lastrowid
                print(f"Queja creada con ID: {complaint_id}")

                # Guardar archivos adjuntos si los hay
                if uploaded_files:
                    # Crear tabla de adjuntos si no existe
                    create_attachments_table = """
                        CREATE TABLE IF NOT EXISTS complaint_attachments (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            complaint_id INT NOT NULL,
                            original_filename VARCHAR(255) NOT NULL,
                            saved_filename VARCHAR(255) NOT NULL,
                            file_path VARCHAR(500) NOT NULL,
                            file_size INT NOT NULL,
                            file_type VARCHAR(10) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
                        );
                    """
                    cur.execute(create_attachments_table)
                    print("Tabla de adjuntos verificada/creada")

                    # Insertar cada archivo adjunto
                    for file_info in uploaded_files:
                        attachment_query = """
                            INSERT INTO complaint_attachments (
                                complaint_id, original_filename, saved_filename, 
                                file_path, file_size, file_type
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """
                        cur.execute(attachment_query, (
                            complaint_id,
                            file_info['original_name'],
                            file_info['saved_name'],
                            file_info['path'],
                            file_info['size'],
                            file_info['type']
                        ))
                    print(f"Guardados {len(uploaded_files)} archivos adjuntos")

                conn.commit()
                cur.close()
                conn.close()

                # Mensaje de éxito
                success_message = "¡Solicitud enviada correctamente! Te contactaremos pronto."
                if uploaded_files:
                    success_message += f" Se adjuntaron {len(uploaded_files)} archivo(s)."

                return jsonify({
                    "success": True,
                    "message": success_message,
                    "complaint_id": complaint_id,
                    "uploaded_files": len(uploaded_files)
                }), 201

            except mariadb.Error as e:
                print(f"Error de base de datos: {e}")
                import traceback
                traceback.print_exc()
                
                # Limpiar archivos subidos si hay error en BD
                cleanup_uploaded_files(uploaded_files)
                
                return jsonify({
                    "success": False,
                    "message": "Error al guardar la solicitud en la base de datos"
                }), 500

        except Exception as e:
            print(f"Error general en post: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                "success": False,
                "message": "Error interno del servidor"
            }), 500

    # GET - mostrar formulario
    user_data = {
        "full_name": f"{session['name']} {session['last_name']}",
        "email": session['email'],
        "study_area": session.get("study_area", ""),
        "term": session.get("term", "")
    }

    return render_template("post.html", user=user_data)

def cleanup_uploaded_files(uploaded_files):
    """Limpia archivos subidos en caso de error"""
    for file_info in uploaded_files:
        try:
            if app.static_folder:
                file_path = os.path.join(app.static_folder, file_info['path'])
            else:
                file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', file_info['path'])
            
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Archivo limpiado: {file_path}")
        except Exception as e:
            print(f"Error limpiando archivo: {e}")


@app.route("/ticket/<int:ticket_id>")
def ticket_detail(ticket_id):
    print("Entrando a ticket_detail, ticket_id:", ticket_id)
    print("Session actual:", dict(session))
    
    # Verifica autenticación
    if "user_id" not in session:
        print("No autenticado, redirigiendo a /auth")
        return redirect(url_for("auth"))

    # Verifica rol de admin
    if session.get("role") != "admin":
        print("No es admin, redirigiendo a /auth")
        flash("Acceso no autorizado", "error")
        return redirect(url_for("auth"))
    
    conn = get_db_connection()
    if not conn:
        print("No conecta a la base de datos, redirigiendo a /ticket")
        flash("Error de conexión a la base de datos", "error")
        return redirect(url_for("ticket_validation"))
    
    try:
        cur = conn.cursor()
        # Elimina columnas no presentes en la tabla complaint_responses
        query = """
            SELECT 
                c.id, c.complaint_type, c.category, c.subject, 
                c.description, c.incident_date, c.status, c.created_at,
                u.name, u.last_name, u.email, u.study_area, u.term,
                cr.assigned_to, cr.admin_response, cr.resolution_date,
                cr.time_spent
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            LEFT JOIN complaint_responses cr ON c.id = cr.complaint_id
            WHERE c.id = ?
        """
        cur.execute(query, (ticket_id,))
        result = cur.fetchone()
        print("Resultado SQL:", result)
        
        if not result:
            print("Ticket no encontrado, redirigiendo a /ticket")
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
        
        def safe_date_format(date_value):
            if date_value and not isinstance(date_value, str):
                return date_value.strftime('%Y-%m-%d')
            return date_value
        
        ticket_data = {
            'id': result[0],
            'complaint_type': result[1],
            'category': result[2],
            'categoryName': category_names.get(result[2], result[2].title()),
            'subject': result[3],
            'description': result[4],
            'incident_date': safe_date_format(result[5]),
            'status': result[6],
            'created_at': result[7].strftime('%Y-%m-%d %H:%M:%S') if result[7] else "",
            'user': {
                'name': result[8],
                'last_name': result[9],
                'email': result[10],
                'study_area': result[11],
                'term': result[12]
            },
            'response': {
                'assigned_to': result[13],
                'admin_response': result[14],
                'resolution_date': safe_date_format(result[15]),
                'time_spent': float(result[16]) if result[16] is not None else None
            }
        }
        
        cur.close()
        conn.close()
        
        print("Renderizando ticket_resolution.html con ticket_data:", ticket_data)
        return render_template("ticket_resolution.html", ticket=ticket_data)
        
    except mariadb.Error as e:
        print(f"Error de MariaDB al obtener los datos del ticket: {e}")
        flash("Error al obtener los datos del ticket", "error")
        return redirect(url_for("ticket_validation"))
    except Exception as e:
        print(f"Error inesperado al procesar el ticket: {e}")
        flash("Error inesperado al procesar el ticket", "error")
        return redirect(url_for("ticket_validation"))


@app.route('/api/tickets/<int:ticket_id>', methods=['GET'])
def api_ticket_detail(ticket_id):
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Error de conexión a la base de datos"}), 500

    try:
        cur = conn.cursor()
        # Ticket básico y respuesta admin
        query = """
            SELECT c.id, c.complaint_type, c.category, c.subject, c.description, c.incident_date, c.status, c.created_at,
                   u.name, u.last_name, u.email, u.study_area, u.term,
                   cr.assigned_to, cr.admin_response, cr.resolution_date, cr.time_spent
            FROM complaints c
            INNER JOIN users u ON c.user_id = u.id
            LEFT JOIN complaint_responses cr ON c.id = cr.complaint_id
            WHERE c.id = ?
        """
        cur.execute(query, (ticket_id,))
        result = cur.fetchone()
        if not result:
            return jsonify({"success": False, "message": "Ticket not found"}), 404

        # Obtener imagen del usuario (primer imagen en complaint_attachments)
        cur.execute("""
            SELECT file_path FROM complaint_attachments 
            WHERE complaint_id = ? AND file_type IN ('jpg','jpeg','png','gif')
            ORDER BY id ASC LIMIT 1
        """, (ticket_id,))
        user_img_row = cur.fetchone()
        user_image = user_img_row[0] if user_img_row else ""

        # Obtener imagen de resolución (primer imagen en resolution_images)
        cur.execute("""
            SELECT file_path FROM resolution_images
            WHERE complaint_id = ? AND file_type IN ('jpg','jpeg','png','gif')
            ORDER BY id ASC LIMIT 1
        """, (ticket_id,))
        admin_img_row = cur.fetchone()
        admin_image = admin_img_row[0] if admin_img_row else ""

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
        def safe_date_format(date_value):
            return date_value.strftime('%Y-%m-%d') if date_value and not isinstance(date_value, str) else date_value

        ticket_data = {
            'success': True,
            'ticket': {
                'id': result[0],
                'complaint_type': result[1],
                'category': result[2],
                'categoryName': category_names.get(result[2], result[2].title()),
                'subject': result[3],
                'description': result[4],
                'incident_date': safe_date_format(result[5]),
                'status': result[6],
                'created_at': result[7].strftime('%Y-%m-%d %H:%M:%S'),
                'user': {
                    'name': result[8],
                    'last_name': result[9],
                    'email': result[10],
                    'study_area': result[11],
                    'term': result[12]
                },
                'response': {
                    'assigned_to': result[13],
                    'admin_response': result[14],
                    'resolution_date': safe_date_format(result[15]),
                    'time_spent': float(result[16]) if result[16] is not None else None
                },
                'user_image': user_image,
                'admin_image': admin_image
            }
        }
        cur.close()
        conn.close()
        return jsonify(ticket_data)
    except mariadb.Error as e:
        print(f"API Error getting ticket detail: {e}")
        return jsonify({"success": False, "message": "Database error"}), 500

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

@app.route("/ticket")
def ticket_validation():
    """Panel de administración para validación de tickets"""
    # Verificar autenticación y rol de administrador
    if "user_id" not in session:
        flash("Debes iniciar sesión para acceder a esta página", "warning")
        return redirect(url_for("auth"))
    
    if session.get("role") != "admin":
        flash("No tienes permisos para acceder a esta sección", "error")
        return redirect(url_for("index"))
    
    # Renderizar el panel de administración
    return render_template("ticket.html")

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500

def create_app():
    return app
