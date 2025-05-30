from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sys

app = Flask(__name__)
app.secret_key = os.urandom(24) # para usar en servidor y cada que se reinicia el servidor hay que validar la session
#app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey') # para usar en servidor SIN INVALIDACIONES DE SESSION

def get_db_path():
    if getattr(sys, 'frozen', False):  # Si es ejecutable
        appdata = os.getenv('APPDATA') or os.path.expanduser('~')
        data_dir = os.path.join(appdata, 'ControlDinero')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return os.path.join(data_dir, 'db.sqlite3')
    else:
        basedir = os.path.abspath(os.path.dirname(__file__))
        return os.path.join(basedir, 'db.sqlite3')

db_path = get_db_path()

def crear_base_si_no_existe(db_path):
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                descripcion TEXT,
                categoria TEXT,
                monto REAL NOT NULL,
                tipo TEXT CHECK(tipo IN ('Ingreso', 'Gasto')) NOT NULL,
                usuario_id INTEGER NOT NULL,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        ''')
        conn.commit()
        conn.close()

crear_base_si_no_existe(db_path)

def obtener_movimientos():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    user_id = session.get('user_id')
    cur.execute("SELECT * FROM movimientos WHERE usuario_id = ? ORDER BY fecha DESC", (user_id,))
    movimientos = cur.fetchall()
    conn.close()
    return movimientos

def calcular_resumen():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    user_id = session.get('user_id')
    cur.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Ingreso' AND usuario_id = ?", (user_id,))
    ingresos = cur.fetchone()[0] or 0
    cur.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Gasto' AND usuario_id = ?", (user_id,))
    gastos = cur.fetchone()[0] or 0
    conn.close()
    saldo = ingresos - gastos
    return ingresos, gastos, saldo

# --- Decorador para requerir login ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Registro ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO usuarios (nombre, email, password_hash) VALUES (?, ?, ?)", (nombre, email, password_hash))
            conn.commit()
            flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('El correo ya está registrado.', 'danger')
        finally:
            conn.close()
    return render_template('register.html')

# --- Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, password_hash FROM usuarios WHERE email = ?", (email,))
        user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['user_nombre'] = user[1]
            return redirect(url_for('index'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')
    return render_template('login.html')

# --- Logout ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Proteger rutas ---
@app.route('/')
@login_required
def index():
    movimientos = obtener_movimientos()
    ingresos, gastos, saldo = calcular_resumen()
    return render_template('index.html', movimientos=movimientos,
                           ingresos=ingresos, gastos=gastos, saldo=saldo, user_nombre=session.get('user_nombre'))

@app.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar():
    if request.method == 'POST':
        fecha = request.form['fecha']
        descripcion = request.form['descripcion']
        categoria = request.form.get('categoria', '')
        tipo = request.form['tipo']
        monto = float(request.form['monto'])
        usuario_id = session.get('user_id')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO movimientos (fecha, descripcion, categoria, tipo, monto, usuario_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (fecha, descripcion, categoria, tipo, monto, usuario_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('agregar.html', user_nombre=session.get('user_nombre'))

@app.route('/eliminar', methods=['GET'])
@login_required
def mostrar_eliminar():
    movimientos = obtener_movimientos()
    return render_template('eliminar.html', movimientos=movimientos, user_nombre=session.get('user_nombre'))

@app.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    usuario_id = session.get('user_id')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM movimientos WHERE id = ? AND usuario_id = ?", (id, usuario_id))
    conn.commit()
    conn.close()
    return redirect(url_for('mostrar_eliminar'))

@app.route('/estadisticas')
@login_required
def estadisticas():
    ingresos, gastos, saldo = calcular_resumen()
    return render_template('estadisticas.html', ingresos=ingresos, gastos=gastos, saldo=saldo, user_nombre=session.get('user_nombre'))

# Filtro para formatear montos con puntos y comas
@app.template_filter('format_miles')
def format_miles(value):
    try:
        value = float(value)
        return '{:,.2f}'.format(value).replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return value

if __name__ == '__main__':
    app.run(debug=True)
