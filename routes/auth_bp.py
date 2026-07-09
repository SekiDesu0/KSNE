from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from models.models import Worker
from utils import validate_rut, format_rut

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin.admin_rendiciones'))
        return redirect(url_for('worker.worker_dashboard'))

    if request.method == 'POST':
        raw_rut = request.form['rut']
        password = request.form['password']

        rut = format_rut(raw_rut) if validate_rut(raw_rut) else raw_rut

        user = Worker.query.filter_by(rut=rut).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            session['rut'] = rut

            if user.is_admin:
                return redirect(url_for('admin.admin_rendiciones'))
            else:
                return redirect(url_for('worker.worker_dashboard'))
        else:
            flash("RUT o contraseña incorrectos.", "danger")

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))
