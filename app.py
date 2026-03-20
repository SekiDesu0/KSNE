from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re
import random
import string
from functools import wraps
from datetime import date

app = Flask(__name__)
app.secret_key = "super_secret_dev_key"
DB_NAME = "db/rendiciones.db"

# --- Database & Helpers ---

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Zonas
    c.execute('''CREATE TABLE IF NOT EXISTS zonas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL)''')
                  
    # 2. Modulos (Belong to Zonas)
    c.execute('''CREATE TABLE IF NOT EXISTS modulos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  zona_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  FOREIGN KEY (zona_id) REFERENCES zonas(id))''')
                  
    # 3. Productos (Belong to Zonas to enforce unique pricing/commissions per zone)
    c.execute('''CREATE TABLE IF NOT EXISTS productos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  zona_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  price REAL NOT NULL,
                  commission REAL NOT NULL,
                  FOREIGN KEY (zona_id) REFERENCES zonas(id))''')

    # 4. Workers (Now tied to a Modulo)
    # Added modulo_id. It can be NULL for the system admin.
    c.execute('''CREATE TABLE IF NOT EXISTS workers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  rut TEXT UNIQUE NOT NULL,
                  name TEXT NOT NULL,
                  phone TEXT NOT NULL,
                  password_hash TEXT NOT NULL,
                  is_admin BOOLEAN DEFAULT 0,
                  modulo_id INTEGER,
                  FOREIGN KEY (modulo_id) REFERENCES modulos(id))''')
    
    # 5. Rendiciones (The main form headers)
    c.execute('''CREATE TABLE IF NOT EXISTS rendiciones
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  worker_id INTEGER NOT NULL,
                  modulo_id INTEGER NOT NULL,
                  fecha DATE NOT NULL,
                  turno TEXT NOT NULL,
                  venta_tarjeta INTEGER DEFAULT 0,
                  venta_mp INTEGER DEFAULT 0,
                  venta_efectivo INTEGER DEFAULT 0,
                  gastos INTEGER DEFAULT 0,
                  observaciones TEXT,
                  FOREIGN KEY (worker_id) REFERENCES workers(id),
                  FOREIGN KEY (modulo_id) REFERENCES modulos(id))''')

    # 6. Rendicion Items (The individual product quantities sold)
    c.execute('''CREATE TABLE IF NOT EXISTS rendicion_items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  rendicion_id INTEGER NOT NULL,
                  producto_id INTEGER NOT NULL,
                  cantidad INTEGER NOT NULL,
                  precio_historico INTEGER NOT NULL,
                  comision_historica INTEGER NOT NULL,
                  FOREIGN KEY (rendicion_id) REFERENCES rendiciones(id),
                  FOREIGN KEY (producto_id) REFERENCES productos(id))''')
    
    # Ensure default admin exists
    c.execute("SELECT id FROM workers WHERE is_admin = 1")
    if not c.fetchone():
        admin_pass = generate_password_hash("admin123")
        c.execute("INSERT INTO workers (rut, name, phone, password_hash, is_admin) VALUES (?, ?, ?, ?, ?)", 
                  ("1-9", "System Admin", "+56 9 0000 0000", admin_pass, 1))
                  
    conn.commit()
    conn.close()

def generate_random_password(length=6):
    """Generates a simple alphanumeric password."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def validate_rut(rut):
    rut_clean = re.sub(r'[^0-9kK]', '', rut).upper()
    if len(rut_clean) < 2: return False
    body, dv = rut_clean[:-1], rut_clean[-1]
    try:
        body_reversed = reversed(body)
        total = sum(int(digit) * factor for digit, factor in zip(body_reversed, [2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7]))
        calc_dv = 11 - (total % 11)
        if calc_dv == 11: calc_dv = '0'
        elif calc_dv == 10: calc_dv = 'K'
        else: calc_dv = str(calc_dv)
        return calc_dv == dv
    except ValueError:
        return False

def format_rut(rut):
    rut_clean = re.sub(r'[^0-9kK]', '', rut).upper()
    body, dv = rut_clean[:-1], rut_clean[-1]
    body_fmt = f"{int(body):,}".replace(',', '.')
    return f"{body_fmt}-{dv}"

def validate_phone(phone):
    phone_clean = re.sub(r'\D', '', phone)
    if phone_clean.startswith('56'): phone_clean = phone_clean[2:]
    return len(phone_clean) == 9

def format_phone(phone):
    phone_clean = re.sub(r'\D', '', phone)
    if phone_clean.startswith('56'): phone_clean = phone_clean[2:]
    return f"+56 {phone_clean[-9]} {phone_clean[-8:-4]} {phone_clean[-4:]}"

# --- Decorators ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash("Acceso denegado. Se requieren permisos de administrador.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def index(): # Cambiado de 'login' a 'index'
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin_rendiciones'))
        return redirect(url_for('worker_dashboard'))
    
    if request.method == 'POST':
        raw_rut = request.form['rut']
        password = request.form['password']
        
        rut = format_rut(raw_rut) if validate_rut(raw_rut) else raw_rut

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, password_hash, is_admin FROM workers WHERE rut = ?", (rut,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['is_admin'] = user[2]
            session['rut'] = rut # Stores RUT for the navbar
            
            if user[2]:
                # This line changed: Redirects to the rendiciones list instead of workers
                return redirect(url_for('admin_rendiciones'))
            else:
                return redirect(url_for('worker_dashboard')) 
        else:
            flash("RUT o contraseña incorrectos.", "danger")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def worker_dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 1. Identificar al trabajador y su zona asignada
    c.execute('''SELECT w.modulo_id, m.name, z.id, z.name 
                 FROM workers w 
                 JOIN modulos m ON w.modulo_id = m.id 
                 JOIN zonas z ON m.zona_id = z.id 
                 WHERE w.id = ?''', (session['user_id'],))
    worker_info = c.fetchone()

    if not worker_info:
        conn.close()
        return "Error: No tienes un módulo asignado. Contacta al administrador."

    modulo_id, modulo_name, zona_id, zona_name = worker_info

    # 2. Manejo del envío del formulario
    if request.method == 'POST':
        fecha = request.form.get('fecha')
        turno = request.form.get('turno')
        
        # Función para limpiar puntos y validar presencia de datos
        def clean_and_validate(val):
            if val is None or val.strip() == "":
                return None
            try:
                return int(val.replace('.', ''))
            except ValueError:
                return None

        # Captura y validación de campos obligatorios
        tarjeta = clean_and_validate(request.form.get('venta_tarjeta'))
        mp = clean_and_validate(request.form.get('venta_mp'))
        efectivo = clean_and_validate(request.form.get('venta_efectivo'))
        gastos = clean_and_validate(request.form.get('gastos')) or 0
        obs = request.form.get('observaciones', '').strip()

        # VERIFICACIÓN: Todos los campos de venta deben estar rellenos
        if tarjeta is None or mp is None or efectivo is None or not fecha or not turno:
            flash("Error: Todos los campos (Fecha, Turno, Tarjeta, MP y Efectivo) son obligatorios. Use 0 si no hubo ventas.", "danger")
            return redirect(url_for('worker_dashboard'))

        # CÁLCULOS ADICIONALES (Para lógica de negocio o auditoría futura)
        total_digital = tarjeta + mp
        total_ventas_general = total_digital + efectivo

        # Insertar Cabecera de Rendición
        c.execute('''INSERT INTO rendiciones 
                     (worker_id, modulo_id, fecha, turno, venta_tarjeta, venta_mp, venta_efectivo, gastos, observaciones) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                  (session['user_id'], modulo_id, fecha, turno, tarjeta, mp, efectivo, gastos, obs))
        rendicion_id = c.lastrowid

        # Insertar Productos (Solo aquellos con cantidad > 0)
        for key, value in request.form.items():
            if key.startswith('qty_') and value and int(value) > 0:
                prod_id = int(key.split('_')[1])
                cantidad = int(value)
                
                c.execute("SELECT price, commission FROM productos WHERE id = ?", (prod_id,))
                prod_data = c.fetchone()
                
                if prod_data:
                    c.execute('''INSERT INTO rendicion_items 
                                 (rendicion_id, producto_id, cantidad, precio_historico, comision_historica) 
                                 VALUES (?, ?, ?, ?, ?)''', 
                              (rendicion_id, prod_id, cantidad, prod_data[0], prod_data[1]))

        conn.commit()
        flash(f"Rendición enviada exitosamente. Total General Declarado: ${total_ventas_general:,}".replace(',', '.'), "success")
        return redirect(url_for('worker_dashboard'))

    # 3. Cargar Productos para la solicitud GET
    c.execute("SELECT id, name, price, commission FROM productos WHERE zona_id = ? ORDER BY name", (zona_id,))
    productos = c.fetchall()
    conn.close()

    has_commission = any(prod[3] > 0 for prod in productos)

    return render_template('worker_dashboard.html', 
                           modulo_name=modulo_name, 
                           zona_name=zona_name, 
                           productos=productos,
                           has_commission=has_commission,
                           today=date.today().strftime('%Y-%m-%d'))
                           
@app.route('/admin/workers', methods=['GET', 'POST'])
@admin_required
def manage_workers():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    form_data = {} 

    if request.method == 'POST':
        raw_rut = request.form['rut']
        raw_phone = request.form['phone']
        name = request.form['name'].strip()
        modulo_id = request.form.get('modulo_id')
        form_data = request.form 

        if not validate_rut(raw_rut):
            flash("El RUT ingresado no es válido.", "danger")
        elif not validate_phone(raw_phone):
            flash("El teléfono debe tener 9 dígitos válidos.", "danger")
        elif not modulo_id:
            flash("Debes asignar un módulo al trabajador.", "danger")
        else:
            rut = format_rut(raw_rut)
            phone = format_phone(raw_phone)
            password = generate_random_password()
            p_hash = generate_password_hash(password)
            
            try:
                # Now inserting modulo_id
                c.execute("INSERT INTO workers (rut, name, phone, password_hash, is_admin, modulo_id) VALUES (?, ?, ?, ?, 0, ?)", 
                          (rut, name, phone, p_hash, modulo_id))
                conn.commit()
                flash(f"Trabajador guardado. Contraseña temporal: <strong>{password}</strong>", "success")
                return redirect(url_for('manage_workers')) 
            except sqlite3.IntegrityError:
                flash("El RUT ya existe en el sistema.", "danger")

    # Fetch workers and JOIN their module name
    c.execute('''SELECT w.id, w.rut, w.name, w.phone, m.name, w.modulo_id 
                 FROM workers w 
                 LEFT JOIN modulos m ON w.modulo_id = m.id 
                 WHERE w.is_admin = 0''')
    workers = c.fetchall()
    
    # Fetch modules and their zones for the dropdown
    c.execute('''SELECT m.id, m.name, z.name 
                 FROM modulos m 
                 JOIN zonas z ON m.zona_id = z.id 
                 ORDER BY z.name, m.name''')
    modulos = c.fetchall()
    
    conn.close()
    return render_template('admin_workers.html', workers=workers, form=form_data, modulos=modulos)


@app.route('/admin/workers/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_worker(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    if request.method == 'POST':
        raw_phone = request.form['phone']
        name = request.form['name'].strip()
        modulo_id = request.form.get('modulo_id')

        if not validate_phone(raw_phone):
            flash("El teléfono debe tener 9 dígitos válidos.", "danger")
            return redirect(url_for('edit_worker', id=id))
        elif not modulo_id:
            flash("Debes seleccionar un módulo.", "danger")
            return redirect(url_for('edit_worker', id=id))

        c.execute("UPDATE workers SET name=?, phone=?, modulo_id=? WHERE id=?", 
                  (name, format_phone(raw_phone), modulo_id, id))
        conn.commit()
        flash("Trabajador actualizado exitosamente.", "success")
        conn.close()
        return redirect(url_for('manage_workers'))

    # Added modulo_id to SELECT
    c.execute("SELECT id, rut, name, phone, modulo_id FROM workers WHERE id=?", (id,))
    worker = c.fetchone()
    
    c.execute('''SELECT m.id, m.name, z.name 
                 FROM modulos m 
                 JOIN zonas z ON m.zona_id = z.id 
                 ORDER BY z.name, m.name''')
    modulos = c.fetchall()
    
    conn.close()
    
    if not worker: return redirect(url_for('manage_workers'))
    return render_template('edit_worker.html', worker=worker, modulos=modulos)
@app.route('/admin/workers/delete/<int:id>', methods=['POST'])
@admin_required
def delete_worker(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM workers WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Trabajador eliminado.", "info")
    return redirect(url_for('manage_workers'))

@app.route('/admin/workers/reset_password/<int:id>', methods=['POST'])
@admin_required
def admin_reset_password(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT name FROM workers WHERE id=?", (id,))
    worker = c.fetchone()
    
    if not worker:
        conn.close()
        return redirect(url_for('manage_workers'))
        
    new_password = generate_random_password()
    p_hash = generate_password_hash(new_password)
    
    c.execute("UPDATE workers SET password_hash=? WHERE id=?", (p_hash, id))
    conn.commit()
    conn.close()
    
    flash(f"Contraseña de {worker[0]} restablecida. La nueva contraseña es: <strong>{new_password}</strong>", "warning")
    
    return redirect(url_for('manage_workers'))


@app.route('/admin/estructura', methods=['GET', 'POST'])
@admin_required
def manage_structure():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_zona':
            name = request.form.get('zona_name').strip()
            try:
                c.execute("INSERT INTO zonas (name) VALUES (?)", (name,))
                conn.commit()
                flash("Zona guardada exitosamente.", "success")
            except sqlite3.IntegrityError:
                flash("Ese nombre de Zona ya existe.", "danger")
                
        elif action == 'add_modulo':
            name = request.form.get('modulo_name').strip()
            zona_id = request.form.get('zona_id')
            if not zona_id:
                flash("Debes seleccionar una Zona válida.", "danger")
            else:
                c.execute("INSERT INTO modulos (zona_id, name) VALUES (?, ?)", (zona_id, name))
                conn.commit()
                flash("Módulo guardado exitosamente.", "success")
                
        return redirect(url_for('manage_structure'))

    # Fetch Zonas
    c.execute("SELECT id, name FROM zonas ORDER BY name")
    zonas = c.fetchall()
    
    # Fetch Modulos with their parent Zona name
    c.execute('''SELECT m.id, m.name, z.name 
                 FROM modulos m 
                 JOIN zonas z ON m.zona_id = z.id 
                 ORDER BY z.name, m.name''')
    modulos = c.fetchall()
    
    conn.close()
    return render_template('admin_structure.html', zonas=zonas, modulos=modulos)

@app.route('/admin/estructura/delete/<string:type>/<int:id>', methods=['POST'])
@admin_required
def delete_structure(type, id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        if type == 'zona':
            # SQLite doesn't enforce foreign keys by default unless PRAGMA foreign_keys = ON
            # But we should manually prevent orphan modules just in case.
            c.execute("SELECT id FROM modulos WHERE zona_id=?", (id,))
            if c.fetchone():
                flash("No puedes eliminar una Zona que tiene Módulos asignados.", "danger")
            else:
                c.execute("DELETE FROM zonas WHERE id=?", (id,))
                flash("Zona eliminada.", "info")
        elif type == 'modulo':
            c.execute("SELECT id FROM workers WHERE modulo_id=?", (id,))
            if c.fetchone():
                flash("No puedes eliminar un Módulo que tiene Trabajadores asignados.", "danger")
            else:
                c.execute("DELETE FROM modulos WHERE id=?", (id,))
                flash("Módulo eliminado.", "info")
        conn.commit()
    except Exception as e:
        flash("Error al eliminar el registro.", "danger")
    finally:
        conn.close()
        
    return redirect(url_for('manage_structure'))

@app.route('/admin/productos', methods=['GET', 'POST'])
@admin_required
def manage_products():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name').strip()
        zona_id = request.form.get('zona_id')
        
        # Strip the formatting dots before trying to convert to math
        raw_price = request.form.get('price').replace('.', '')
        raw_commission = request.form.get('commission').replace('.', '')

        if not zona_id:
            flash("Debes seleccionar una Zona.", "danger")
        else:
            try:
                # Force strictly whole numbers
                price = int(raw_price)
                commission = int(raw_commission)
                
                c.execute("INSERT INTO productos (zona_id, name, price, commission) VALUES (?, ?, ?, ?)", 
                          (zona_id, name, price, commission))
                conn.commit()
                flash("Producto guardado exitosamente.", "success")
            except ValueError:
                flash("El precio y la comisión deben ser números enteros válidos.", "danger")
        
        return redirect(url_for('manage_products'))

    c.execute("SELECT id, name FROM zonas ORDER BY name")
    zonas = c.fetchall()

    c.execute('''SELECT p.id, p.name, p.price, p.commission, z.name, p.zona_id 
                 FROM productos p
                 JOIN zonas z ON p.zona_id = z.id
                 ORDER BY z.name, p.name''')
    productos = c.fetchall()
    
    conn.close()
    return render_template('admin_productos.html', zonas=zonas, productos=productos)

@app.route('/admin/productos/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_product(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name').strip()
        zona_id = request.form.get('zona_id')
        
        # Strip formatting dots
        raw_price = request.form.get('price').replace('.', '')
        raw_commission = request.form.get('commission').replace('.', '')

        try:
            price = int(raw_price)
            commission = int(raw_commission)
            
            c.execute("UPDATE productos SET zona_id=?, name=?, price=?, commission=? WHERE id=?",
                      (zona_id, name, price, commission, id))
            conn.commit()
            flash("Producto actualizado exitosamente.", "success")
            conn.close()
            return redirect(url_for('manage_products'))
        except ValueError:
            flash("El precio y la comisión deben ser números enteros válidos.", "danger")

    # GET request - fetch data for the form
    c.execute("SELECT id, name FROM zonas ORDER BY name")
    zonas = c.fetchall()

    c.execute("SELECT id, zona_id, name, price, commission FROM productos WHERE id=?", (id,))
    producto = c.fetchone()
    conn.close()

    if not producto:
        return redirect(url_for('manage_products'))

    return render_template('edit_producto.html', zonas=zonas, producto=producto)

@app.route('/admin/productos/delete/<int:id>', methods=['POST'])
@admin_required
def delete_product(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM productos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Producto eliminado.", "info")
    return redirect(url_for('manage_products'))

@app.route('/admin/rendiciones')
@admin_required
def admin_rendiciones():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Fetch all rendiciones, newest first
    c.execute('''
        SELECT r.id, r.fecha, w.name, m.name, r.turno,
               (r.venta_tarjeta + r.venta_mp + r.venta_efectivo) as total_declarado,
               r.gastos
        FROM rendiciones r
        JOIN workers w ON r.worker_id = w.id
        JOIN modulos m ON r.modulo_id = m.id
        ORDER BY r.fecha DESC, r.id DESC
    ''')
    rendiciones = c.fetchall()
    conn.close()
    
    return render_template('admin_rendiciones.html', rendiciones=rendiciones)

@app.route('/admin/rendiciones/<int:id>')
@admin_required
def view_rendicion(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Get Header Info
    c.execute('''
        SELECT r.id, r.fecha, w.name, m.name, r.turno,
               r.venta_tarjeta, r.venta_mp, r.venta_efectivo, r.gastos, r.observaciones
        FROM rendiciones r
        JOIN workers w ON r.worker_id = w.id
        JOIN modulos m ON r.modulo_id = m.id
        WHERE r.id = ?
    ''', (id,))
    rendicion = c.fetchone()

    if not rendicion:
        conn.close()
        flash("Rendición no encontrada.", "danger")
        return redirect(url_for('admin_rendiciones'))

    # Get Line Items
    c.execute('''
        SELECT p.name, ri.cantidad, ri.precio_historico, ri.comision_historica,
               (ri.cantidad * ri.precio_historico) as total_linea,
               (ri.cantidad * ri.comision_historica) as total_comision
        FROM rendicion_items ri
        JOIN productos p ON ri.producto_id = p.id
        WHERE ri.rendicion_id = ?
    ''', (id,))
    items = c.fetchall()
    conn.close()

    # Calculate the mathematical truth vs what they declared
    total_calculado = sum(item[4] for item in items)
    comision_total = sum(item[5] for item in items)

    return render_template('admin_rendicion_detail.html', 
                           rendicion=rendicion, 
                           items=items,
                           total_calculado=total_calculado,
                           comision_total=comision_total)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)