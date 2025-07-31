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
            password VARCHAR(100) NOT NULL,
            user_id VARCHAR(100) NOT NULL UNIQUE,
            role ENUM('admin', 'client') NOT NULL,
            name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            study_area VARCHAR(100) NOT NULL,
            study_speciality VARCHAR(100) NOT NULL,
            term TINYINT NOT NULL
        );
    """
    try:
        cur.execute(schema)
        conn.commit()
    except mariadb.Error as e:
        print(f"Create user table error: {e}")
        sys.exit(1)

def initDB():
    pass


