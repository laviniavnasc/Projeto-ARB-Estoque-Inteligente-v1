from werkzeug.security import generate_password_hash
import mysql.connector
import os

config = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "estoque_inteligente"),
}

conn = mysql.connector.connect(**config)
cur = conn.cursor()
password_hash = generate_password_hash("SUA_SENHA_AQUI")
cur.execute("""
    INSERT INTO users (name, login, password_hash)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE password_hash=VALUES(password_hash)
""", ("Administrador", "admin", password_hash))
conn.commit()
cur.close()
conn.close()
print("Usuário administrador criado/atualizado com sucesso.")
