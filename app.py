
from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import os  # <- AÑADIDO

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
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host='0.0.0.0', port=port)

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import mysql.connector
from datetime import datetime, timedelta
from fpdf import FPDF
import io
import os

app = Flask(__name__)
app.secret_key = 'secreto123'

# Conexión a la base de datos
db = mysql.connector.connect(
    host="database-1.cbmc846qcmg5.sa-east-1.rds.amazonaws.com",
    user="admin",
    password="Vamosperu10_",
    database="restaurante_marisol"
)

# Reintentar conexión si se pierde
def get_db():
    global db
    try:
        db.ping(reconnect=True, attempts=3, delay=2)
    except mysql.connector.Error:
        db = mysql.connector.connect(
            host="database-1.cbmc846qcmg5.sa-east-1.rds.amazonaws.com",
            user="admin",
            password="Vamosperu10_",
            database="restaurante_marisol"
        )
    return db

@app.route('/')
def index():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT * FROM mesas")
    mesas = cursor.fetchall()
    return render_template('mesas.html', mesas=mesas)

@app.route('/atender/<int:id_mesa>', methods=['GET', 'POST'])
def atender_mesa(id_mesa):
    if request.method == 'POST':
        nombres = request.form['nombres']
        apellidos = request.form['apellidos']
        dni = request.form['dni']
        telefono = request.form['telefono']

        cursor = get_db().cursor()
        cursor.execute("INSERT INTO clientes (nombres, apellidos, dni, telefono) VALUES (%s, %s, %s, %s)",
                       (nombres, apellidos, dni, telefono))
        id_cliente = cursor.lastrowid

        cursor.execute("UPDATE mesas SET estado = 'ocupada' WHERE id_mesa = %s", (id_mesa,))
        cursor.execute("INSERT INTO pedidos (id_mesa, id_cliente) VALUES (%s, %s)", (id_mesa, id_cliente))
        get_db().commit()

        flash("✅ Cliente registrado y pedido iniciado.")
        return redirect(url_for('colocar_pedido', id_mesa=id_mesa))

    return render_template('atender.html', id_mesa=id_mesa)

@app.route('/pedido/<int:id_mesa>')
def colocar_pedido(id_mesa):
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT id_pedido FROM pedidos WHERE id_mesa = %s ORDER BY fecha DESC LIMIT 1", (id_mesa,))
    pedido = cursor.fetchone()
    if not pedido:
        flash("❌ No hay pedido activo para esta mesa.")
        return redirect(url_for('index'))

    id_pedido = pedido['id_pedido']
    cursor.execute("SELECT * FROM productos WHERE cantidad > 0")
    productos = cursor.fetchall()

    cursor.execute("""
        SELECT d.id_detalle, p.nombre, d.cantidad, d.precio, d.subtotal 
        FROM detalle_pedido d
        JOIN productos p ON d.id_producto = p.id_producto
        WHERE d.id_pedido = %s
    """, (id_pedido,))
    detalle = cursor.fetchall()

    total = sum([item['subtotal'] for item in detalle])
    return render_template('pedido.html', productos=productos, detalle=detalle, id_pedido=id_pedido, id_mesa=id_mesa, total=total)

@app.route('/agregar_producto', methods=['POST'])
def agregar_producto():
    id_pedido = request.form['id_pedido']
    id_producto = request.form['id_producto']
    cantidad = int(request.form['cantidad'])

    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT precio, cantidad FROM productos WHERE id_producto = %s", (id_producto,))
    producto = cursor.fetchone()

    if not producto:
        flash("❌ Producto no encontrado.")
        return redirect(url_for('colocar_pedido', id_mesa=request.form['id_mesa']))

    if cantidad > producto['cantidad']:
        flash("⚠️ Cantidad insuficiente.")
        return redirect(url_for('colocar_pedido', id_mesa=request.form['id_mesa']))

    precio = producto['precio']
    subtotal = precio * cantidad

    cursor.execute("""
        INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, precio, subtotal)
        VALUES (%s, %s, %s, %s, %s)
    """, (id_pedido, id_producto, cantidad, precio, subtotal))

    cursor.execute("UPDATE productos SET cantidad = cantidad - %s WHERE id_producto = %s", (cantidad, id_producto))
    get_db().commit()

    flash("✅ Producto agregado al pedido.")
    return redirect(url_for('colocar_pedido', id_mesa=request.form['id_mesa']))

@app.route('/generar_boleta/<int:id_pedido>')
def generar_boleta(id_pedido):
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("""
        SELECT c.nombres, c.apellidos, c.dni, p.fecha, m.id_mesa
        FROM pedidos p
        JOIN clientes c ON p.id_cliente = c.id_cliente
        JOIN mesas m ON m.id_mesa = p.id_mesa
        WHERE p.id_pedido = %s
    """, (id_pedido,))
    pedido = cursor.fetchone()

    if not pedido:
        flash("❌ Pedido no encontrado.")
        return redirect(url_for('index'))

    cursor.execute("""
        SELECT pr.nombre, d.cantidad, d.precio, d.subtotal
        FROM detalle_pedido d
        JOIN productos pr ON d.id_producto = pr.id_producto
        WHERE d.id_pedido = %s
    """, (id_pedido,))
    detalle = cursor.fetchall()

    total = sum(item['subtotal'] for item in detalle)

    # Generar boleta PDF con estilo profesional
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Encabezado principal
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, "BOLETA ELECTRONICA", ln=True, align="C")

    # Datos del restaurante (sin emojis)
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 8, "Restaurante Marisol", ln=True, align="C")
    pdf.cell(200, 6, "Direccion: Calle La Pasion con La Unidad - Asoc. Puerta del Sol", ln=True, align="C")
    pdf.cell(200, 6, "Los Olivos, Lima - Peru", ln=True, align="C")
    pdf.cell(200, 6, "RUC: 20481234567 | Tel: (01) 456-7890", ln=True, align="C")
    pdf.cell(200, 6, "-" * 40, ln=True, align="C")

    # Datos del pedido
    pdf.ln(4)
    pdf.cell(200, 8, f"Fecha: {pedido['fecha'].strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.cell(200, 8, f"Cliente: {pedido['nombres']} {pedido['apellidos']}  |  DNI: {pedido['dni']}", ln=True)
    pdf.cell(200, 8, f"Mesa N°: {pedido['id_mesa']}", ln=True)
    pdf.cell(200, 6, "-" * 40, ln=True)

    # Detalle del pedido
    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(80, 8, "Producto", border=0)
    pdf.cell(30, 8, "Cantidad", border=0, align="C")
    pdf.cell(40, 8, "Precio", border=0, align="C")
    pdf.cell(40, 8, "Subtotal", border=0, align="R")
    pdf.ln()

    pdf.set_font("Arial", "", 12)
    for item in detalle:
        pdf.cell(80, 8, item['nombre'], border=0)
        pdf.cell(30, 8, str(item['cantidad']), border=0, align="C")
        pdf.cell(40, 8, f"S/. {item['precio']:.2f}", border=0, align="C")
        pdf.cell(40, 8, f"S/. {item['subtotal']:.2f}", border=0, align="R")
        pdf.ln()

    # Línea final y total
    pdf.cell(200, 6, "-" * 40, ln=True)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(150, 10, "TOTAL A PAGAR:", align="R")
    pdf.cell(40, 10, f"S/. {total:.2f}", ln=True, align="R")

    # Pie de página
    pdf.ln(8)
    pdf.set_font("Arial", "I", 11)
    pdf.cell(200, 8, "Gracias por su visita, vuelva pronto.", ln=True, align="C")

    # Devolver PDF
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name='boleta.pdf')


@app.route('/finalizar_pedido/<int:id_mesa>', methods=['POST'])
def finalizar_pedido(id_mesa):
    cursor = get_db().cursor()
    cursor.execute("UPDATE mesas SET estado = 'libre' WHERE id_mesa = %s", (id_mesa,))
    get_db().commit()
    flash(f"✅ Mesa {id_mesa} liberada y pedido cerrado.")
    return redirect(url_for('index'))

@app.route('/estado_mesas')
def estado_mesas():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("SELECT * FROM mesas")
    mesas = cursor.fetchall()
    return jsonify(mesas)

@app.route('/historial')
def historial():
    cursor = get_db().cursor(dictionary=True)
    cursor.execute("""
        SELECT r.id_reserva, c.nombres, c.apellidos, r.fecha_reserva, r.hora_reserva, r.estado
        FROM reservas r
        JOIN clientes c ON r.id_cliente = c.id_cliente
        ORDER BY r.fecha_reserva DESC
    """)
    reservas = cursor.fetchall()

    for r in reservas:
        if isinstance(r['hora_reserva'], timedelta):
            r['hora_reserva'] = (datetime.min + r['hora_reserva']).time()

    return render_template('historial.html', reservas=reservas)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)



