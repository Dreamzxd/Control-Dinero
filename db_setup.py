# archivo: db_setup.py
import sqlite3

DB_PATH = 'db.sqlite3'

def crear_tablas():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    ''')
    c.execute("PRAGMA table_info(movimientos)")
    columnas = [col[1] for col in c.fetchall()]
    if 'usuario_id' not in columnas:
        usuario_id_default = input('¿A qué usuario (id) quieres asignar los movimientos antiguos? (deja vacío para NULL): ')
        if usuario_id_default.strip() == '':
            usuario_id_default = 'NULL'
        c.execute('ALTER TABLE movimientos RENAME TO movimientos_old')
        c.execute('''
        CREATE TABLE movimientos (
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
        c.execute(f'''
        INSERT INTO movimientos (id, fecha, descripcion, categoria, monto, tipo, usuario_id)
        SELECT id, fecha, descripcion, categoria, monto, tipo, {usuario_id_default} FROM movimientos_old
        ''')
        c.execute('DROP TABLE movimientos_old')
        print('Columna usuario_id agregada a movimientos.')
    else:
        print('La columna usuario_id ya existe en movimientos.')
    conn.commit()
    conn.close()
    print('Tablas creadas o verificadas correctamente.')

def mostrar_tablas():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tablas = c.fetchall()
    print('Tablas en la base de datos:')
    for t in tablas:
        print(' -', t[0])
    conn.close()

def mostrar_contenido(tabla):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(f'SELECT * FROM {tabla}')
        filas = c.fetchall()
        columnas = [desc[0] for desc in c.description]
        print(' | '.join(columnas))
        for fila in filas:
            print(' | '.join(str(x) for x in fila))
    except Exception as e:
        print('Error:', e)
    conn.close()

if __name__ == '__main__':
    print('Opciones:')
    print('1. Crear/verificar tablas')
    print('2. Ver tablas existentes')
    print('3. Ver contenido de una tabla')
    opcion = input('Elige una opción (1/2/3): ')
    if opcion == '1':
        crear_tablas()
    elif opcion == '2':
        mostrar_tablas()
    elif opcion == '3':
        tabla = input('Nombre de la tabla: ')
        mostrar_contenido(tabla)
    else:
        print('Opción no válida.')
