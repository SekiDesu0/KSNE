import re
import random
import string
from functools import wraps
from flask import session, redirect, url_for, flash, request
from datetime import date

def generate_random_password(length=6):
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

def get_report_params():
        """Captura filtros de la URL o establece valores por defecto."""
        hoy = date.today()
        anio = request.args.get('anio', str(hoy.year))
        mes = request.args.get('mes', f"{hoy.month:02d}")
        dia = request.args.get('dia')
        worker_id = request.args.get('worker_id')
        return anio, mes, dia, worker_id

def get_common_report_data(c, modulo_id):
    """Obtiene nombre del módulo y lista de trabajadores para los filtros."""
    c.execute("SELECT name FROM modulos WHERE id = ?", (modulo_id,))
    modulo_info = c.fetchone()
    
    c.execute('''
        SELECT DISTINCT w.id, w.name 
        FROM workers w 
        WHERE w.modulo_id = ? AND w.is_admin = 0
        ORDER BY w.name
    ''', (modulo_id,))
    workers = c.fetchall()
    
    c.execute("SELECT DISTINCT strftime('%Y', fecha) as anio FROM rendiciones ORDER BY anio DESC")
    anios = [row[0] for row in c.fetchall()]
    if str(date.today().year) not in anios:
        anios.insert(0, str(date.today().year))
        
    return modulo_info[0] if modulo_info else "Módulo", workers, anios