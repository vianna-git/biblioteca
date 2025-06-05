from flask import Flask, render_template, request, redirect, url_for
import database
import psycopg2
import random

app = Flask(__name__)

DATABASE_NAME = "biblioteca_db"
database.DB_NAME = DATABASE_NAME

OPCOES_EDICAO_ESPECIAL = ['Edição Única', 'Volume Único']

@app.route('/')
def listar_livros():
    """Lista todos os livros."""
    query = """
        SELECT
            l.id,
            l.nome,
            l.tipo,
            l.genero,
            l.editora,
            l.localizacao,
            l.edicao,
            l.mangaka,
            l.informacoes, -- Novo campo
            STRING_AGG(a.nome, ', ') AS autores_nomes
        FROM
            livros l
        LEFT JOIN
            livro_autor la ON l.id = la.livro_id
        LEFT JOIN
            autores a ON la.autor_id = a.id
        GROUP BY
            l.id, l.nome, l.tipo, l.genero, l.editora, l.localizacao, l.edicao, l.mangaka, l.informacoes
        ORDER BY
            l.nome ASC;
    """
    livros = database.fetch_all(query)
    return render_template('index.html', livros=livros)

@app.route('/adicionar', methods=['GET', 'POST'])
def adicionar_livro():
    """Exibe o formulário para adicionar um novo livro e processa a submissão."""
    if request.method == 'POST':
        nome = request.form['nome']
        tipo = request.form['tipo']
        genero = request.form['genero']
        editora = request.form.get('editora')
        localizacao = request.form['localizacao']
        autores_input = request.form.getlist('autor')
        edicao = request.form.get('edicao_input')
        edicao_especial = request.form.get('edicao_especial')
        informacoes = request.form.get('informacoes') # Novo campo

        final_edicao = edicao_especial if edicao_especial else edicao
        mangaka = request.form.get('mangaka')

        try:
            query_livro = "INSERT INTO livros (nome, tipo, genero, editora, localizacao, edicao, mangaka, informacoes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"
            livro_id = database.fetch_last_inserted_id(query_livro, (nome, tipo, genero, editora, localizacao, final_edicao, mangaka if tipo == 'Mangá' else None, informacoes))

            if livro_id:
                if tipo != 'Mangá':
                    for autor_nome in autores_input:
                        autor_nome = autor_nome.strip()
                        if autor_nome:
                            autor_tuple = database.fetch_one("SELECT id FROM autores WHERE nome = %s", (autor_nome,))
                            autor_id = autor_tuple[0] if autor_tuple else None

                            if autor_id is None:
                                autor_id = database.fetch_last_inserted_id("INSERT INTO autores (nome) VALUES (%s) RETURNING id", (autor_nome,))

                            if autor_id:
                                database.execute_query("INSERT INTO livro_autor (livro_id, autor_id) VALUES (%s, %s) ON CONFLICT (livro_id, autor_id) DO NOTHING", (livro_id, autor_id))
            return redirect(url_for('listar_livros'))

        except psycopg2.Error as e:
            print(f"Erro ao adicionar livro: {e}")
            pass
        except ValueError as e:
            print(f"Erro de valor: {e}")
            pass

    tipos_db = [t[0] for t in database.fetch_all_tipos()]
    generos_db = [g[0] for g in database.fetch_all_generos()]
    localizacoes_db = [l[0] for l in database.fetch_all_localizacoes()]

    return render_template('adicionar_livro.html', tipos=tipos_db,
                           generos=generos_db,
                           localizacoes=localizacoes_db,
                           opcoes_edicao_especial=OPCOES_EDICAO_ESPECIAL)

@app.route('/buscar', methods=['GET', 'POST'])
def buscar_livros():
    """Exibe o formulário de busca e processa a busca."""
    resultados = []
    # Adicionado 'Informações' como campo de busca
    campos_busca = ['Nome', 'Tipo', 'Gênero', 'Autor/Mangaká', 'Editora', 'Localização', 'Número(s) de Edições', 'Informações']

    if request.method == 'POST':
        termo = request.form.get('termo')
        campo = request.form.get('campo_busca')

        if termo and campo:
            termo_lower = '%' + termo.lower() + '%'
            conn = database.get_db_connection()
            if conn:
                cursor = conn.cursor()
                query = ""
                params = ()

                # Incluir 'informacoes' em todas as queries para exibir
                select_clause = "SELECT id, nome, tipo, genero, editora, localizacao, edicao, mangaka, informacoes FROM livros"

                if campo == 'Nome':
                    query = f"{select_clause} WHERE LOWER(nome) LIKE %s ORDER BY nome"
                    params = (termo_lower,)
                elif campo == 'Tipo':
                    query = f"{select_clause} WHERE LOWER(tipo) LIKE %s ORDER BY nome"
                    params = (termo_lower,)
                elif campo == 'Gênero':
                    query = f"{select_clause} WHERE LOWER(genero) LIKE %s ORDER BY nome"
                    params = (termo_lower,)
                elif campo == 'Editora':
                    query = f"{select_clause} WHERE LOWER(editora) LIKE %s ORDER BY nome"
                    params = (termo_lower,)
                elif campo == 'Localização':
                    query = f"{select_clause} WHERE LOWER(localizacao) LIKE %s ORDER BY nome"
                    params = (termo_lower,)
                elif campo == 'Número(s) de Edições': # Campo de busca atualizado
                    query = f"{select_clause} WHERE LOWER(edicao) LIKE %s ORDER BY nome"
                    params = (termo_lower,)
                elif campo == 'Informações': # Novo campo de busca
                    query = f"{select_clause} WHERE LOWER(informacoes) LIKE %s ORDER BY nome"
                    params = (termo_lower,)
                elif campo == 'Autor/Mangaká':
                    query = """
                        SELECT DISTINCT l.id, l.nome, l.tipo, l.genero, l.editora, l.localizacao, l.edicao, l.mangaka, l.informacoes
                        FROM livros l
                        LEFT JOIN livro_autor la ON l.id = la.livro_id
                        LEFT JOIN autores a ON la.autor_id = a.id
                        WHERE LOWER(l.mangaka) LIKE %s OR LOWER(a.nome) LIKE %s
                        ORDER BY l.nome;
                    """
                    params = (termo_lower, termo_lower)

                try:
                    cursor.execute(query, params)
                    resultados = cursor.fetchall()
                except psycopg2.Error as e:
                    print(f"Erro na busca: {e}")
                finally:
                    cursor.close()
                    conn.close()

    return render_template('busca.html', campos_busca=campos_busca, resultados=resultados)

@app.route('/deletar/<int:livro_id>', methods=['POST'])
def deletar_livro(livro_id):
    """Deleta um livro do banco de dados."""
    if database.execute_query("DELETE FROM livros WHERE id = %s", (livro_id,)):
        return redirect(url_for('listar_livros'))
    else:
        return "Erro ao deletar o livro. Verifique os logs.", 500

@app.route('/editar/<int:livro_id>', methods=['GET', 'POST'])
def editar_livro(livro_id):
    """Exibe o formulário para editar um livro e processa a submissão."""
    livro = None
    autores_livro = []

    # Incluir 'informacoes' na busca
    query_livro = "SELECT id, nome, tipo, genero, editora, localizacao, edicao, mangaka, informacoes FROM livros WHERE id = %s"
    livro_data = database.fetch_one(query_livro, (livro_id,))

    if livro_data:
        livro = {
            'id': livro_data[0],
            'nome': livro_data[1],
            'tipo': livro_data[2],
            'genero': livro_data[3],
            'editora': livro_data[4],
            'localizacao': livro_data[5],
            'edicao': livro_data[6],
            'mangaka': livro_data[7],
            'informacoes': livro_data[8] # Novo campo
        }
        if livro['tipo'] != 'Mangá':
            autores_raw = database.fetch_all("""
                SELECT a.nome FROM autores a
                JOIN livro_autor la ON a.id = la.autor_id
                WHERE la.livro_id = %s ORDER BY a.nome
            """, (livro_id,))
            autores_livro = [a[0] for a in autores_raw]

    if request.method == 'POST':
        nome = request.form['nome']
        tipo = request.form['tipo']
        genero = request.form['genero']
        editora = request.form.get('editora')
        localizacao = request.form['localizacao']
        autores_input = request.form.getlist('autor')
        edicao = request.form.get('edicao_input')
        edicao_especial = request.form.get('edicao_especial')
        informacoes = request.form.get('informacoes') # Novo campo

        final_edicao = edicao_especial if edicao_especial else edicao
        mangaka = request.form.get('mangaka')

        # Incluir 'informacoes' no UPDATE
        query_update_livro = """
            UPDATE livros
            SET nome = %s, tipo = %s, genero = %s, editora = %s, localizacao = %s, edicao = %s, mangaka = %s, informacoes = %s
            WHERE id = %s
        """
        success = database.execute_query(query_update_livro, (
            nome, tipo, genero, editora, localizacao,
            final_edicao,
            mangaka if tipo == 'Mangá' else None,
            informacoes, # Novo campo
            livro_id
        ))

        if success:
            if tipo != 'Mangá':
                database.execute_query("DELETE FROM livro_autor WHERE livro_id = %s", (livro_id,))

                for autor_nome in autores_input:
                # ... (restante da lógica de autores) ...
                    autor_nome = autor_nome.strip()
                    if autor_nome:
                        autor_tuple = database.fetch_one("SELECT id FROM autores WHERE nome = %s", (autor_nome,))
                        autor_id = autor_tuple[0] if autor_tuple else None

                        if autor_id is None:
                            autor_id = database.fetch_last_inserted_id("INSERT INTO autores (nome) VALUES (%s) RETURNING id", (autor_nome,))

                        if autor_id:
                            database.execute_query("INSERT INTO livro_autor (livro_id, autor_id) VALUES (%s, %s) ON CONFLICT (livro_id, autor_id) DO NOTHING", (livro_id, autor_id))
            else:
                database.execute_query("DELETE FROM livro_autor WHERE livro_id = %s", (livro_id,))

            return redirect(url_for('listar_livros'))
        else:
            return "Erro ao atualizar o livro.", 500

    tipos_db = [t[0] for t in database.fetch_all_tipos()]
    generos_db = [g[0] for g in database.fetch_all_generos()]
    localizacoes_db = [l[0] for l in database.fetch_all_localizacoes()]

    if livro:
        return render_template('editar_livro.html', livro=livro, autores_livro=autores_livro,
                               tipos=tipos_db, generos=generos_db, localizacoes=localizacoes_db,
                               opcoes_edicao_especial=OPCOES_EDICAO_ESPECIAL)
    else:
        return "Livro não encontrado.", 404

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """Página de administração para gerenciar gêneros, tipos e localizações."""
    if request.method == 'POST':
        if 'novo_genero' in request.form:
            novo_genero = request.form['novo_genero'].strip()
            if novo_genero:
                database.insert_genero(novo_genero)
        elif 'novo_tipo' in request.form:
            novo_tipo = request.form['novo_tipo'].strip()
            if novo_tipo:
                database.insert_tipo(novo_tipo)
        elif 'nova_localizacao' in request.form:
            nova_localizacao = request.form['nova_localizacao'].strip()
            if nova_localizacao:
                database.insert_localizacao(nova_localizacao)
        return redirect(url_for('admin'))

    generos = database.fetch_all_generos()
    tipos = database.fetch_all_tipos()
    localizacoes = database.fetch_all_localizacoes()

    return render_template('admin.html', generos=generos, tipos=tipos, localizacoes=localizacoes)

@app.route('/sugerir_graphic_novel')
def sugerir_graphic_novel():
    """Sugere uma Graphic Novel aleatoriamente."""
    query_ids = "SELECT id FROM livros WHERE tipo = 'Graphic Novel'"
    graphic_novel_ids_raw = database.fetch_all(query_ids)

    graphic_novel_ids = [item[0] for item in graphic_novel_ids_raw]

    sugestao = None
    if graphic_novel_ids:
        random_id = random.choice(graphic_novel_ids)

        # Incluir 'informacoes' na busca
        query_sugestao = """
            SELECT
                l.id,
                l.nome,
                l.tipo,
                l.genero,
                l.editora,
                l.localizacao,
                l.edicao,
                l.mangaka,
                l.informacoes, -- Novo campo
                STRING_AGG(a.nome, ', ') AS autores_nomes
            FROM
                livros l
            LEFT JOIN
                livro_autor la ON l.id = la.livro_id
            LEFT JOIN
                autores a ON la.autor_id = a.id
            WHERE
                l.id = %s
            GROUP BY
                l.id, l.nome, l.tipo, l.genero, l.editora, l.localizacao, l.edicao, l.mangaka, l.informacoes;
        """
        sugestao_raw = database.fetch_one(query_sugestao, (random_id,))

        if sugestao_raw:
            sugestao = {
                'id': sugestao_raw[0],
                'nome': sugestao_raw[1],
                'tipo': sugestao_raw[2],
                'genero': sugestao_raw[3],
                'editora': sugestao_raw[4],
                'localizacao': sugestao_raw[5],
                'edicao': sugestao_raw[6],
                'mangaka': sugestao_raw[7],
                'informacoes': sugestao_raw[8], # Novo campo
                'autores_nomes': sugestao_raw[9]
            }

    return render_template('sugestao_graphic_novel.html', sugestao=sugestao)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')