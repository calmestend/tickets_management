import sys
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
        sys.exit(1)

conn = get_db_connection()
cur = conn.cursor()

def init_users():
    schema = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            user_id VARCHAR(100) NOT NULL UNIQUE,
            role ENUM('admin', 'student') NOT NULL DEFAULT 'student',
            name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            study_area VARCHAR(100) NOT NULL,
            study_speciality VARCHAR(100),
            term TINYINT NOT NULL,
            avatar_initials VARCHAR(5),
            personal_description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
    """
    try:
        cur.execute(schema)
        conn.commit()
    except mariadb.Error as e:
        print(f"Error creating users table: {e}")
        sys.exit(1)

def init_complaints():
    schema = """
        CREATE TABLE IF NOT EXISTS complaints (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            complaint_type ENUM('queja', 'sugerencia', 'peticion') NOT NULL,
            category ENUM(
                'servicios-academicos', 
                'infraestructura', 
                'servicios-estudiantiles', 
                'tecnologia', 
                'administrativo', 
                'biblioteca', 
                'cafeteria', 
                'otro'
            ) NOT NULL,
            priority ENUM('alta', 'media', 'baja') NOT NULL DEFAULT 'media',
            subject VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            incident_date DATE,
            status ENUM('pendiente', 'en-proceso', 'resuelto', 'escalado') DEFAULT 'pendiente',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """
    try:
        cur.execute(schema)
        conn.commit()
    except mariadb.Error as e:
        print(f"Error creating compaints table: {e}")
        sys.exit(1)

def init_complaint_responses():
    schema = """
        CREATE TABLE IF NOT EXISTS complaint_responses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            complaint_id INT NOT NULL,
            assigned_to VARCHAR(100),
            admin_response TEXT,
            resolution_date DATE,
            time_spent DECIMAL(4,2),
            follow_up_required BOOLEAN DEFAULT FALSE,
            follow_up_date DATE,
            internal_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
        );
    """
    try:
        cur.execute(schema)
        conn.commit()
    except mariadb.Error as e:
        print(f"Error compaint_responsens table: {e}")
        sys.exit(1)

def create_indexes():
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_complaints_user_id ON complaints(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);",
        "CREATE INDEX IF NOT EXISTS idx_complaints_created_at ON complaints(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_complaints_priority ON complaints(priority);",
        "CREATE INDEX IF NOT EXISTS idx_complaints_category ON complaints(category);",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
        "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);"
    ]
    
    try:
        for index in indexes:
            cur.execute(index)
        conn.commit()
        print("✅ Índices creados exitosamente")
    except mariadb.Error as e:
        print(f"❌ Error al crear índices: {e}")

def insert_sample_data():
    try:
        admin_user = """
            INSERT INTO users (email, password, user_id, role, name, last_name, 
                             study_area, study_speciality, term, avatar_initials, 
                             personal_description) 
            VALUES (
                'admin@utc.edu.mx', 
                'hashed_password_admin', 
                'UTC001', 
                'admin', 
                'María', 
                'González López', 
                'Administración', 
                'Gestión Educativa', 
                1, 
                'MG', 
                'Administradora del sistema de quejas y sugerencias'
            ) ON DUPLICATE KEY UPDATE email=email;
        """
        
        student_user = """
            INSERT INTO users (email, password, user_id, role, name, last_name, 
                             study_area, study_speciality, term, avatar_initials, 
                             personal_description) 
            VALUES (
                'juan.perez@utc.edu.mx', 
                'hashed_password_student', 
                'UTC002', 
                'student', 
                'Juan', 
                'Pérez Díaz', 
                'Ingeniería en Sistemas', 
                'Desarrollo Web', 
                6, 
                'JP', 
                'Estudiante apasionado por la tecnología y el desarrollo de software.'
            ) ON DUPLICATE KEY UPDATE email=email;
        """
        
        cur.execute(admin_user)
        cur.execute(student_user)

        sample_complaint = """
            INSERT INTO complaints (
                user_id, complaint_type, category, priority, 
                subject, description, incident_date, status
            ) 
            VALUES (
                2, 
                'queja', 
                'servicios-academicos', 
                'alta', 
                'Problema con inscripción a materias optativas', 
                'No he podido inscribirme a las materias optativas del semestre debido a problemas técnicos en el sistema. He intentado varias veces pero siempre me aparece un error.',
                '2025-07-20',
                'pendiente'
            );
        """
        
        cur.execute(sample_complaint)
        conn.commit()
        
    except mariadb.Error as e:
        print(f"Error inserting data: {e}")


def initDB():
    init_users()
    init_complaints()
    init_complaint_responses()
    
    create_indexes()
    
    insert_sample_data()

def get_user_by_email(email):
    try:
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        return cur.fetchone()
    except mariadb.Error as e:
        print(f"Error al obtener usuario: {e}")
        return None

def get_complaints_by_user(user_id):
    try:
        cur.execute("""
            SELECT c.*, cr.admin_response, cr.resolution_date 
            FROM complaints c 
            LEFT JOIN complaint_responses cr ON c.id = cr.complaint_id 
            WHERE c.user_id = ? 
            ORDER BY c.created_at DESC
        """, (user_id,))
        return cur.fetchall()
    except mariadb.Error as e:
        print(f"Error al obtener quejas del usuario: {e}")
        return []

def get_pending_complaints():
    try:
        cur.execute("""
            SELECT c.*, u.name, u.last_name, u.email 
            FROM complaints c 
            JOIN users u ON c.user_id = u.id 
            WHERE c.status = 'pendiente' 
            ORDER BY c.priority DESC, c.created_at ASC
        """, )
        return cur.fetchall()
    except mariadb.Error as e:
        print(f"Error al obtener quejas pendientes: {e}")
        return []

def create_complaint(user_id, complaint_data):
    try:
        query = """
            INSERT INTO complaints (
                user_id, complaint_type, category, priority, 
                subject, description, incident_date, 
                expected_resolution, previous_attempts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cur.execute(query, (
            user_id,
            complaint_data['type'],
            complaint_data['category'],
            complaint_data['priority'],
            complaint_data['subject'],
            complaint_data['description'],
            complaint_data.get('incident_date'),
            complaint_data.get('expected_resolution'),
            complaint_data.get('previous_attempts')
        ))
        conn.commit()
        return cur.lastrowid
    except mariadb.Error as e:
        print(f"Error al crear queja: {e}")
        return None

def update_complaint_response(complaint_id, response_data):
    try:
        cur.execute("""
            UPDATE complaints 
            SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (response_data['status'], complaint_id))
        
        query = """
            INSERT INTO complaint_responses (
                complaint_id, assigned_to, admin_response, 
                resolution_date, time_spent, follow_up_required, 
                follow_up_date, internal_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON DUPLICATE KEY UPDATE
                assigned_to = VALUES(assigned_to),
                admin_response = VALUES(admin_response),
                resolution_date = VALUES(resolution_date),
                time_spent = VALUES(time_spent),
                follow_up_required = VALUES(follow_up_required),
                follow_up_date = VALUES(follow_up_date),
                internal_notes = VALUES(internal_notes),
                updated_at = CURRENT_TIMESTAMP
        """
        
        cur.execute(query, (
            complaint_id,
            response_data['assigned_to'],
            response_data['admin_response'],
            response_data.get('resolution_date'),
            response_data.get('time_spent'),
            response_data.get('follow_up_required', False),
            response_data.get('follow_up_date'),
            response_data.get('internal_notes')
        ))
        
        conn.commit()
        return True
    except mariadb.Error as e:
        print(f"Error al actualizar respuesta: {e}")
        return False

initDB()
