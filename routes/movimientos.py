from flask import Blueprint, render_template, request, redirect
import sqlite3

movimientos = Blueprint("movimientos", __name__)

def conectar_db():
    return sqlite3.connect("movimientos.db")

@movimientos.route("/agregar", methods=["GET", "POST"])
def agregar():
    if request.method == "POST":
        fecha = request.form["fecha"]
        descripcion = request.form["descripcion"]
        categoria = request.form["categoria"]
        monto = float(request.form["monto"])
        tipo = request.form["tipo"]

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO movimientos (fecha, descripcion, categoria, monto, tipo)
            VALUES (?, ?, ?, ?, ?)
        """, (fecha, descripcion, categoria, monto, tipo))
        conn.commit()
        conn.close()

        return redirect("/")
    else:
        return render_template("agregar.html")
