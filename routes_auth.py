from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from database import get_db_connection
from utils import validate_rut, format_rut

def register_auth_routes(app):
    @app.route('/', methods=['GET', 'POST'])
    def index():
        if 'user_id' in session:
            if session.get('is_admin'):
                return redirect(url_for('admin_rendiciones'))
            return redirect(url_for('worker_dashboard'))
        
        if request.method == 'POST':
            raw_rut = request.form['rut']
            password = request.form['password']
            
            rut = format_rut(raw_rut) if validate_rut(raw_rut) else raw_rut

            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT id, password_hash, is_admin FROM workers WHERE rut = ?", (rut,))
            user = c.fetchone()
            conn.close()

            if user and check_password_hash(user[1], password):
                session['user_id'] = user[0]
                session['is_admin'] = user[2]
                session['rut'] = rut
                
                if user[2]:
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