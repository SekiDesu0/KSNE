import re
import random
import string
from functools import wraps
from flask import session, redirect, url_for, flash

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