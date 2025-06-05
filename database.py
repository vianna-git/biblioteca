import psycopg2
import os

# Configurações de conexão com o banco de dados
# Prioriza variáveis de ambiente definidas pelo Docker Compose ou fallback para valores padrão
DB_HOST = os.environ.get('DATABASE_HOST', 'postgres_db')
DB_NAME = os.environ.get('DATABASE_NAME', 'biblioteca_db')
DB_USER = os.environ.get('DATABASE_USER', 'user')
DB_PASS = os.environ.get('DATABASE_PASSWORD', 'password')
DB_PORT = os.environ.get('DATABASE_PORT', '5432')

def get_db_connection():
    """Retorna uma conexão com o banco de dados PostgreSQL."""
    conn = None
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT)
    except psycopg2.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        # Em um ambiente de produção, você pode querer registrar este erro
        # e talvez não retornar a conexão ou levantar uma exceção.
    return conn

def fetch_one(query, params=()):
    """Executa uma query e retorna o primeiro resultado."""
    conn = get_db_connection()
    result = None
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            result = cur.fetchone()
        except psycopg2.Error as e:
            print(f"Erro na query fetch_one: {e}")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    return result

def fetch_all(query, params=()):
    """Executa uma query e retorna todos os resultados."""
    conn = get_db_connection()
    results = []
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            results = cur.fetchall()
        except psycopg2.Error as e:
            print(f"Erro na query fetch_all: {e}")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    return results

def execute_query(query, params=()):
    """Executa uma query de modificação (INSERT, UPDATE, DELETE)."""
    conn = get_db_connection()
    success = False
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            success = True
        except psycopg2.Error as e:
            conn.rollback() # Reverte a transação em caso de erro
            print(f"Erro na query execute_query: {e}")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    return success

def fetch_last_inserted_id(query, params=()):
    """
    Executa uma query de inserção e retorna o ID inserido.
    A query deve incluir 'RETURNING id' para funcionar corretamente.
    """
    conn = get_db_connection()
    inserted_id = None
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            result = cur.fetchone()
            if result:
                inserted_id = result[0]
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Erro na query fetch_last_inserted_id: {e}")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    return inserted_id

# Funções para buscar gêneros, tipos e localizações para os formulários de administração
def fetch_all_generos():
    """Busca todos os gêneros disponíveis no banco de dados."""
    # A coluna 'nome' é usada para o nome do gênero, que é o primeiro (índice 0) elemento da tupla.
    return fetch_all("SELECT nome FROM generos_admin ORDER BY nome")

def fetch_all_tipos():
    """Busca todos os tipos disponíveis no banco de dados."""
    return fetch_all("SELECT nome FROM tipos_admin ORDER BY nome")

def fetch_all_localizacoes():
    """Busca todas as localizações disponíveis no banco de dados."""
    return fetch_all("SELECT nome FROM localizacoes_admin ORDER BY nome")

def insert_genero(nome):
    """Insere um novo gênero no banco de dados, se não existir."""
    return execute_query("INSERT INTO generos_admin (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING", (nome,))

def insert_tipo(nome):
    """Insere um novo tipo no banco de dados, se não existir."""
    return execute_query("INSERT INTO tipos_admin (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING", (nome,))

def insert_localizacao(nome):
    """Insere uma nova localização no banco de dados, se não existir."""
    return execute_query("INSERT INTO localizacoes_admin (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING", (nome,))