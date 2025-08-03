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
        print(f"Error creating complaints table: {e}")
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
        );
    """
    try:
        cur.execute(schema)
        conn.commit()
    except mariadb.Error as e:
        print(f"Error creating complaint_responses table: {e}")
        sys.exit(1)

def create_indexes():
    indexes = [
        "CREATE INDEX idx_complaints_user_id ON complaints(user_id);",
        "CREATE INDEX idx_complaints_status ON complaints(status);",
        "CREATE INDEX idx_complaints_created_at ON complaints(created_at);",
        "CREATE INDEX idx_complaints_category ON complaints(category);",
        "CREATE INDEX idx_users_email ON users(email);",
        "CREATE INDEX idx_users_user_id ON users(user_id);",
        "CREATE INDEX idx_users_role ON users(role);"
    ]
    
    for index in indexes:
        try:
            cur.execute(index)
        except mariadb.Error as e:
            if "Duplicate key name" in str(e):
                print(f"ℹ️ Índice ya existe, se omite: {index.split()[2]}")
            else:
                print(f"❌ Error al crear índice: {e}")
    conn.commit()
    print("✅ Índices verificados/creados")

def insert_sample_data():
    try:
        admin_user = """
            INSERT INTO users (email, password, user_id, role, name, last_name, 
                               study_area, study_speciality, term, avatar_initials, 
                               personal_description) 
            VALUES (
                'admin@utc.edu.mx', 
                '222', 
                '1111111112', 
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
                '123', 
                '1111111111', 
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

        # Obtener ID del usuario estudiante (por si cambia)
        cur.execute("SELECT id FROM users WHERE email = 'juan.perez@utc.edu.mx'")
        student_id = cur.fetchone()[0]

        sample_complaint = """
            INSERT INTO complaints (
                user_id, complaint_type, category,  
                subject, description, incident_date, status
            ) 
            VALUES (
                ?, 
                'queja', 
                'servicios-academicos', 
                'Problema con inscripción a materias optativas', 
                'No he podido inscribirme a las materias optativas del semestre debido a problemas técnicos en el sistema. He intentado varias veces pero siempre me aparece un error.',
                '2025-07-20',
                'pendiente'
            );
        """

        cur.execute(sample_complaint, (student_id,))
        conn.commit()
        print("✅ Datos de prueba insertados correctamente")
    except mariadb.Error as e:
        print(f"❌ Error inserting data: {e}")



def initDB():
    init_users()
    init_complaints()
    init_complaint_responses()
    create_indexes()
    insert_sample_data()

if __name__ == "__main__":
    initDB()

