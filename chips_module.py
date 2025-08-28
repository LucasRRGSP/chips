# chips_module.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import psycopg2, os
from datetime import date, timedelta

CHIPS_BP = Blueprint("chips", __name__, template_folder="templates")

def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres")
    )

# Listagem
@CHIPS_BP.route("/chips")
def listar_chips():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chips ORDER BY id DESC")
    chips = cur.fetchall()
    conn.close()
    return render_template("chips_list.html", chips=chips)

# Novo chip
@CHIPS_BP.route("/chips/novo", methods=["GET", "POST"])
def novo_chip():
    if request.method == "POST":
        numero = request.form["numero"]
        status = request.form["status"]
        ultima = request.form.get("ultima_utilizacao") or None
        proxima = request.form.get("proxima_disponibilidade") or None
        obs = request.form.get("observacoes")

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO chips (numero_chip, status, ultima_utilizacao, proxima_disponibilidade, observacoes)
            VALUES (%s, %s, %s, %s, %s)
        """, (numero, status, ultima, proxima, obs))
        conn.commit()
        conn.close()
        flash("Chip adicionado com sucesso!", "success")
        return redirect(url_for("chips.listar_chips"))
    return render_template("chips_form.html", chip=None)

# Editar chip
@CHIPS_BP.route("/chips/editar/<int:id>", methods=["GET", "POST"])
def editar_chip(id):
    conn = get_db()
    cur = conn.cursor()
    if request.method == "POST":
        numero = request.form["numero"]
        status = request.form["status"]
        ultima = request.form.get("ultima_utilizacao") or None
        proxima = request.form.get("proxima_disponibilidade") or None
        obs = request.form.get("observacoes")

        cur.execute("""
            UPDATE chips SET numero_chip=%s, status=%s, ultima_utilizacao=%s, proxima_disponibilidade=%s, observacoes=%s
            WHERE id=%s
        """, (numero, status, ultima, proxima, obs, id))
        conn.commit()
        conn.close()
        flash("Chip atualizado!", "success")
        return redirect(url_for("chips.listar_chips"))
    else:
        cur.execute("SELECT * FROM chips WHERE id=%s", (id,))
        chip = cur.fetchone()
        conn.close()
        return render_template("chips_form.html", chip=chip)

# Deletar
@CHIPS_BP.route("/chips/deletar/<int:id>", methods=["POST"])
def deletar_chip(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM chips WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    flash("Chip removido!", "danger")
    return redirect(url_for("chips.listar_chips"))
