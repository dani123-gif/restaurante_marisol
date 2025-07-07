from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

def get_connection():
    return mysql.connector.connect(
        host="database-1.cbmc846qcmg5.sa-east-1.rds.amazonaws.com",
        user="admin",
        password="Vamosperu10_",
        database="restaurante_marisol"
    )

@app.route('/')
def mostrar_productos():
    db = get_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos ORDER BY categoria, nombre")
    productos = cursor.fetchall()
    db.close()

    categorias = {}
    for producto in productos:
        categoria = producto['categoria']
        if categoria not in categorias:
            categorias[categoria] = []
        categorias[categoria].append(producto)

    return render_template('producto.html', categorias=categorias)

@app.route('/aumentar/<int:id_producto>', methods=['POST'])
def aumentar_stock(id_producto):
    cantidad = int(request.form['cantidad'])
    db = get_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE productos SET cantidad = cantidad + %s WHERE id_producto = %s", (cantidad, id_producto))
    db.commit()
    db.close()
    return redirect(url_for('mostrar_productos'))

if __name__ == '__main__':
port = int(os.environ.get("PORT", 10000))
app.run(host='0.0.0.0', port=port)

