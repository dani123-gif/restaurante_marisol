import os
from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Conexión a tu base de datos
db = mysql.connector.connect(
    host="database-1.cbmc846qcmg5.sa-east-1.rds.amazonaws.com",
    user="admin",
    password="Vamosperu10_",
    database="restaurante_marisol"
)

@app.route('/')
def mostrar_productos():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos ORDER BY categoria, nombre")
    productos = cursor.fetchall()
    cursor.close()

    # Agrupar por categoría
    categorias = {}
    for producto in productos:
        cat = producto['categoria']
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(producto)

    return render_template('productos.html', categorias=categorias)

# ✅ Ruta para aumentar cantidad de producto
@app.route('/aumentar/<int:id_producto>', methods=['POST'])
def aumentar_cantidad(id_producto):
    try:
        cantidad = int(request.form['cantidad'])
        cursor = db.cursor()
        cursor.execute("UPDATE productos SET cantidad = cantidad + %s WHERE id_producto = %s", (cantidad, id_producto))
        db.commit()
        cursor.close()
    except:
        pass
    return redirect(url_for('mostrar_productos'))

# ✅ Ejecutar en red local y localhost
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)