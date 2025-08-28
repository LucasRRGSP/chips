import os
from flask import Flask, request, redirect, url_for, flash, render_template_string
import psycopg2
import pandas as pd
import chardet
from datetime import date, timedelta, datetime

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY","chave_secreta_teste")

# ===============================
# Banco de Dados
# ===============================
def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST","localhost"),
        port=os.getenv("DB_PORT","5432"),
        database=os.getenv("DB_NAME","postgres"),
        user=os.getenv("DB_USER","postgres"),
        password=os.getenv("DB_PASSWORD","postgress")
    )

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chips (
        id SERIAL PRIMARY KEY,
        numero_chip VARCHAR(20) NOT NULL,
        status VARCHAR(20) NOT NULL CHECK (status IN ('disponivel','banido','em_uso')),
        ultima_utilizacao DATE,
        primeira_recarga DATE,
        proxima_recarga DATE,
        proxima_utilizacao DATE,
        data_banimento DATE,
        observacoes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()

init_db()

# ===============================
# Funções utilitárias
# ===============================
def ler_csv_auto(path):
    with open(path,"rb") as f:
        raw_data = f.read()
        encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
    try:
        return pd.read_csv(path, encoding=encoding)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding=encoding, errors="ignore")

def str_para_date(valor):
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        try:
            return datetime.strptime(valor, "%Y-%m-%d").date()
        except:
            return None
    return None

# ===============================
# Formulário Novo/Editar Chip
# ===============================
def form_chip(chip=None):
    numero = chip[1] if chip else ""
    status = chip[2] if chip else "disponivel"
    ultima = chip[3] if chip else ""
    primeira = chip[4] if chip else ""
    proxima = chip[5] if chip else ""
    observacoes = chip[8] if chip else ""
    return render_template_string("""
    <html>
    <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-dark text-light">
    <div class="container mt-4">
        <h2>{{ '✏️ Editar Chip' if chip else '➕ Novo Chip' }}</h2>
        <form method="POST">
            <div class="mb-3"><label>Número</label><input type="text" name="numero" class="form-control" value="{{ numero }}" required></div>
            <div class="mb-3"><label>Status</label>
                <select name="status" class="form-select" required>
                    <option value="disponivel" {% if status=="disponivel" %}selected{% endif %}>Disponível</option>
                    <option value="banido" {% if status=="banido" %}selected{% endif %}>Banido</option>
                    <option value="em_uso" {% if status=="em_uso" %}selected{% endif %}>Em Uso</option>
                </select>
            </div>
            <div class="mb-3"><label>Última Utilização</label><input type="date" name="ultima_utilizacao" class="form-control" value="{{ ultima }}"></div>
            <div class="mb-3"><label>Primeira Recarga</label><input type="date" name="primeira_recarga" class="form-control" value="{{ primeira }}"></div>
            <div class="mb-3"><label>Próxima Recarga</label><input type="date" name="proxima_recarga" class="form-control" value="{{ proxima }}"></div>
            <div class="mb-3"><label>Observações</label><textarea name="observacoes" class="form-control">{{ observacoes }}</textarea></div>
            <div class="d-flex gap-2">
                <button type="submit" class="btn btn-success flex-fill">Salvar</button>
                <a href="{{ url_for('listar_chips') }}" class="btn btn-secondary flex-fill">Cancelar</a>
            </div>
        </form>
    </div>
    </body>
    </html>
    """, chip=chip, numero=numero, status=status, ultima=ultima, primeira=primeira, proxima=proxima, observacoes=observacoes)

# ===============================
# Dashboard / Listagem Chips
# ===============================
@app.route("/")
def index():
    return redirect(url_for("listar_chips"))

@app.route("/chips")
def listar_chips():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chips ORDER BY id DESC")
    chips_raw = cur.fetchall()
    conn.close()

    hoje = date.today()
    alertas = []
    chips_display = []

    for c in chips_raw:
        ultima_utilizacao = str_para_date(c[3])
        primeira_recarga = str_para_date(c[4])
        proxima_recarga = str_para_date(c[5])
        proxima_utilizacao = str_para_date(c[6])
        data_banimento = str_para_date(c[7])
        row_class = ""

        if c[2] == "banido":
            row_class = "table-danger"
            if proxima_utilizacao:
                alertas.append(f"⏰ Chip {c[1]} poderá ser usado a partir de {proxima_utilizacao.strftime('%d/%m/%Y')}")
        elif proxima_recarga and (proxima_recarga - hoje).days <= 5:
            row_class = "table-warning"
            alertas.append(f"🔔 Chip {c[1]} precisa de recarga em breve ({proxima_recarga.strftime('%d/%m/%Y')})")

        chips_display.append({
            "chip": c,
            "row_class": row_class
        })

    template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Dashboard Chips</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            .btn-group .btn { min-width: 100px; }
        </style>
    </head>
    <body class="bg-dark text-light">
    <div class="container mt-4">
        <h2>📱 Dashboard de Chips</h2>
        {% for msg in alertas %}
            <div class="alert alert-warning">{{ msg }}</div>
        {% endfor %}
        <div class="mb-3 d-flex gap-2">
            <a href="{{ url_for('novo_chip') }}" class="btn btn-success">Novo Chip</a>
            <a href="{{ url_for('importar_csv') }}" class="btn btn-info">Importar CSV</a>
        </div>
        <div class="table-responsive">
        <table class="table table-dark table-hover align-middle text-center">
            <thead>
                <tr>
                    <th>ID</th><th>Número</th><th>Status</th>
                    <th>Última Utilização</th><th>Primeira Recarga</th>
                    <th>Próxima Recarga</th><th>Próxima Utilização</th><th>Data Banimento</th><th>Ações</th>
                </tr>
            </thead>
            <tbody>
            {% for item in chips_display %}
                <tr class="{{ item.row_class }}">
                    <td>{{ item.chip[0] }}</td>
                    <td>{{ item.chip[1] }}</td>
                    <td>
                        {% if item.chip[2]=="disponivel" %}
                            <span class="badge bg-success">Disponível</span>
                        {% elif item.chip[2]=="banido" %}
                            <span class="badge bg-danger">Banido</span>
                        {% else %}
                            <span class="badge bg-warning text-dark">Em uso</span>
                        {% endif %}
                    </td>
                    <td>{{ item.chip[3].strftime("%d/%m/%Y") if item.chip[3] else "-" }}</td>
                    <td>{{ item.chip[4].strftime("%d/%m/%Y") if item.chip[4] else "-" }}</td>
                    <td>{{ item.chip[5].strftime("%d/%m/%Y") if item.chip[5] else "-" }}</td>
                    <td>
                        {% if item.chip[2]=="banido" and item.chip[6] %}
                            {{ item.chip[6].strftime("%d/%m/%Y") }}
                        {% else %}
                            -
                        {% endif %}
                    </td>
                    <td>
                        {% if item.chip[2]=="banido" and item.chip[7] %}
                            {{ item.chip[7].strftime("%d/%m/%Y") }}
                        {% else %}
                            -
                        {% endif %}
                    </td>
                    <td>
                        <div class="btn-group" role="group">
                            <a href="{{ url_for('editar_chip', id=item.chip[0]) }}" class="btn btn-primary" title="Editar chip">Editar</a>
                            <a href="{{ url_for('banir_chip', id=item.chip[0]) }}" class="btn btn-danger" title="Banir chip">Banir</a>
                            <a href="{{ url_for('desbanir_chip', id=item.chip[0]) }}" class="btn btn-success" title="Desbanir chip">Desbanir</a>
                            <a href="{{ url_for('recarga_rapida', id=item.chip[0]) }}" class="btn btn-info" title="Recarga rápida">Recarga</a>
                            <a href="{{ url_for('deletar_chip', id=item.chip[0]) }}" class="btn btn-secondary" title="Deletar chip">Deletar</a>
                        </div>
                    </td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
        </div>
    </div>
    </body>
    </html>
    """
    return render_template_string(template, chips_display=chips_display, alertas=alertas)


# ===============================
# CRUD e Ações
# ===============================
def salvar_chip(numero, status, ultima, primeira, proxima, obs):
    """Calcula datas corretamente e retorna tupla pronta para INSERT/UPDATE"""
    if status=="banido":
        data_banimento = date.today()
        proxima_utilizacao = data_banimento + timedelta(days=1)
    else:
        data_banimento = None
        proxima_utilizacao = None
    return (numero,status,ultima,primeira,proxima,proxima_utilizacao,data_banimento,obs)

@app.route("/chips/novo", methods=["GET","POST"])
def novo_chip():
    if request.method=="POST":
        data = salvar_chip(
            request.form["numero"],
            request.form["status"],
            str_para_date(request.form.get("ultima_utilizacao")),
            str_para_date(request.form.get("primeira_recarga")),
            str_para_date(request.form.get("proxima_recarga")),
            request.form.get("observacoes")
        )
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO chips (numero_chip,status,ultima_utilizacao,primeira_recarga,proxima_recarga,
            proxima_utilizacao,data_banimento,observacoes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,data)
        conn.commit()
        conn.close()
        flash("Chip adicionado!", "success")
        return redirect(url_for("listar_chips"))
    return form_chip()

@app.route("/chips/editar/<int:id>", methods=["GET","POST"])
def editar_chip(id):
    conn = get_db()
    cur = conn.cursor()
    if request.method=="POST":
        data = salvar_chip(
            request.form["numero"],
            request.form["status"],
            str_para_date(request.form.get("ultima_utilizacao")),
            str_para_date(request.form.get("primeira_recarga")),
            str_para_date(request.form.get("proxima_recarga")),
            request.form.get("observacoes")
        )
        cur.execute("""
            UPDATE chips SET numero_chip=%s,status=%s,ultima_utilizacao=%s,primeira_recarga=%s,proxima_recarga=%s,
            proxima_utilizacao=%s,data_banimento=%s,observacoes=%s WHERE id=%s
        """, data + (id,))
        conn.commit()
        conn.close()
        flash("Chip atualizado!", "success")
        return redirect(url_for("listar_chips"))
    else:
        cur.execute("SELECT * FROM chips WHERE id=%s",(id,))
        chip = cur.fetchone()
        conn.close()
        return form_chip(chip)

@app.route("/chips/deletar/<int:id>")
def deletar_chip(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM chips WHERE id=%s",(id,))
    conn.commit()
    conn.close()
    flash("Chip deletado!", "danger")
    return redirect(url_for("listar_chips"))

@app.route("/chips/banir/<int:id>")
def banir_chip(id):
    hoje = date.today()
    proxima_utilizacao = hoje + timedelta(days=1)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE chips SET status='banido', data_banimento=%s, proxima_utilizacao=%s WHERE id=%s
    """,(hoje,proxima_utilizacao,id))
    conn.commit()
    conn.close()
    flash("Chip banido!", "warning")
    return redirect(url_for("listar_chips"))

@app.route("/chips/desbanir/<int:id>")
def desbanir_chip(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE chips SET status='disponivel', data_banimento=NULL, proxima_utilizacao=NULL WHERE id=%s
    """,(id,))
    conn.commit()
    conn.close()
    flash("Chip desbanido!", "success")
    return redirect(url_for("listar_chips"))

@app.route("/chips/recarga/<int:id>")
def recarga_rapida(id):
    hoje = date.today()
    proxima_recarga = hoje + timedelta(days=30)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE chips SET ultima_utilizacao=%s, proxima_recarga=%s, status='em_uso' WHERE id=%s
    """,(hoje,proxima_recarga,id))
    conn.commit()
    conn.close()
    flash("Recarga rápida aplicada!", "info")
    return redirect(url_for("listar_chips"))

@app.route("/chips/importar", methods=["GET","POST"])
def importar_csv():
    if request.method=="POST":
        f = request.files.get("csv_file")
        if f:
            df = ler_csv_auto(f)
            conn = get_db()
            cur = conn.cursor()
            for _, row in df.iterrows():
                data = salvar_chip(
                    row.get("numero_chip"),
                    row.get("status","disponivel").lower(),
                    str_para_date(row.get("ultima_utilizacao")),
                    str_para_date(row.get("primeira_recarga")),
                    str_para_date(row.get("proxima_recarga")),
                    row.get("observacoes")
                )
                try:
                    cur.execute("""
                        INSERT INTO chips (numero_chip,status,ultima_utilizacao,
                        primeira_recarga,proxima_recarga,proxima_utilizacao,data_banimento,observacoes)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """, data)
                except Exception as e:
                    print("Erro CSV:", e)
            conn.commit()
            conn.close()
            flash("CSV importado com sucesso!", "success")
            return redirect(url_for("listar_chips"))
    return render_template_string("""
    <html><head>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head><body class="bg-dark text-light">
    <div class="container mt-4">
        <h2>📂 Importar CSV</h2>
        <form method="POST" enctype="multipart/form-data">
            <div class="mb-3">
                <input type="file" name="csv_file" class="form-control" accept=".csv" required>
            </div>
            <button type="submit" class="btn btn-info">Importar</button>
            <a href="{{ url_for('listar_chips') }}" class="btn btn-secondary">Cancelar</a>
        </form>
    </div></body></html>
    """)

if __name__=="__main__":
    app.run(debug=True)
