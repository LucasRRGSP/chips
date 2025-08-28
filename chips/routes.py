from flask import Blueprint, render_template, request, redirect, url_for, flash
import pyodbc
from datetime import datetime
import re

chips_bp = Blueprint('chips', __name__, template_folder='templates')

# Valores válidos para EstadoAtual conforme restrição CHECK no banco
ESTADOS_VALIDOS = ['ativo', 'desconectado', 'banido', 'desbanido']

def get_connection():
    return pyodbc.connect('Driver={SQL Server};Server=localhost;Database=CHIPS;Trusted_Connection=yes;')

def formatar_telefone(numero):
    numeros = re.sub(r'\D', '', numero)
    if len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2]} {numeros[3:7]}-{numeros[7:]}"
    else:
        return numero

@chips_bp.route('/chips')
def listar_chips():
    conn = get_connection()
    cursor = conn.cursor()

    # Filtros
    numero = request.args.get('numero', '').strip()
    estado = request.args.get('estado', '').strip()
    usuario = request.args.get('usuario', '').strip()
    data_ini = request.args.get('data_ini', '').strip()
    data_fim = request.args.get('data_fim', '').strip()

    query = """
        SELECT Id, NumeroCelular, EstadoAtual, Operadora, Status, DataCadastro, Usuario
        FROM Chips
        WHERE 1=1
    """
    params = []

    if numero:
        query += " AND NumeroCelular LIKE ?"
        params.append(f"%{numero}%")
    if estado:
        query += " AND EstadoAtual = ?"
        params.append(estado)
    if usuario:
        query += " AND Usuario LIKE ?"
        params.append(f"%{usuario}%")
    if data_ini:
        query += " AND CONVERT(date, DataCadastro) >= ?"
        params.append(data_ini)
    if data_fim:
        query += " AND CONVERT(date, DataCadastro) <= ?"
        params.append(data_fim)

    query += " ORDER BY Id DESC"
    cursor.execute(query, params)
    chips = cursor.fetchall()
    conn.close()

    return render_template('chips/listar.html', chips=chips)

@chips_bp.route('/chips/novo', methods=['GET', 'POST'])
def novo_chip():
    if request.method == 'POST':
        numero = request.form['NumeroCelular']
        operadora = request.form.get('Operadora', '')
        estado = request.form.get('EstadoAtual', '').lower().strip()
        status = request.form.get('Status', '')
        usuario = request.form.get('Usuario', '')
        data = datetime.now()

        if estado not in ESTADOS_VALIDOS:
            flash(f"Estado inválido: {estado}. Valores permitidos: {', '.join(ESTADOS_VALIDOS)}", 'danger')
            return render_template('chips/formulario.html', chip=request.form)

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Chips (NumeroCelular, EstadoAtual, Operadora, Status, Usuario, DataCadastro)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (numero, estado, operadora, status, usuario, data))
            conn.commit()
        except pyodbc.IntegrityError as e:
            flash(f"Erro ao cadastrar chip: {e}", 'danger')
            return render_template('chips/formulario.html', chip=request.form)
        finally:
            conn.close()

        flash('Chip cadastrado com sucesso!', 'success')
        return redirect(url_for('chips.listar_chips'))

    return render_template('chips/formulario.html', chip=None)

@chips_bp.route('/chips/editar/<int:id>', methods=['GET', 'POST'])
def editar_chip(id):
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        numero = request.form['NumeroCelular']
        operadora = request.form.get('Operadora', '')
        estado = request.form.get('EstadoAtual', '').lower().strip()
        status = request.form.get('Status', '')
        usuario = request.form.get('Usuario', '')

        if estado not in ESTADOS_VALIDOS:
            flash(f"Estado inválido: {estado}. Valores permitidos: {', '.join(ESTADOS_VALIDOS)}", 'danger')
            return render_template('chips/formulario.html', chip=request.form)

        try:
            cursor.execute("""
                UPDATE Chips
                SET NumeroCelular = ?, EstadoAtual = ?, Operadora = ?, Status = ?, Usuario = ?
                WHERE Id = ?
            """, (numero, estado, operadora, status, usuario, id))
            conn.commit()
        except pyodbc.IntegrityError as e:
            flash(f"Erro ao atualizar chip: {e}", 'danger')
            return render_template('chips/formulario.html', chip=request.form)
        finally:
            conn.close()

        flash('Chip atualizado com sucesso!', 'success')
        return redirect(url_for('chips.listar_chips'))

    cursor.execute("SELECT * FROM Chips WHERE Id = ?", (id,))
    chip = cursor.fetchone()
    conn.close()

    if not chip:
        flash('Chip não encontrado.', 'danger')
        return redirect(url_for('chips.listar_chips'))

    return render_template('chips/formulario.html', chip=chip)

@chips_bp.route('/chips/excluir/<int:id>', methods=['POST'])
def excluir_chip(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Chips WHERE Id = ?", (id,))
    conn.commit()
    conn.close()
    flash('Chip excluído com sucesso!', 'success')
    return redirect(url_for('chips.listar_chips'))
