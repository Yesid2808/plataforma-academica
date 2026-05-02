from decouple import config
import psycopg


def check_connection():
    db_name = config("DB_NAME", default="plataforma_academica_v2")
    db_user = config("DB_USER", default="colegio_app")
    db_password = config("DB_PASSWORD", default="")
    db_host = config("DB_HOST", default="localhost")
    db_port = config("DB_PORT", default="5433")
    connect_timeout = config("DB_CONNECT_TIMEOUT", default=5, cast=int)

    try:
        conn = psycopg.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            connect_timeout=connect_timeout,
        )
        print(f"CONEXION EXITOSA: {db_name} en {db_host}:{db_port}")
        conn.close()
    except Exception as exc:
        print(f"ERROR DE CONEXION A {db_name} EN {db_host}:{db_port}:")
        print(exc)


if __name__ == "__main__":
    check_connection()
