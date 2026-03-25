import sqlite3
from flask import app, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from datetime import date, datetime
from database import get_db_connection
from utils import admin_required, validate_rut, format_rut, validate_phone, format_phone, generate_random_password
import calendar

def register_admin_routes(app):
    @app.route('/admin/workers', methods=['GET', 'POST'])
    @admin_required
    def manage_workers():
        conn = get_db_connection()
        c = conn.cursor()
        form_data = {} 

        if request.method == 'POST':
            raw_rut = request.form['rut']
            raw_phone = request.form['phone']
            name = request.form['name'].strip()
            modulo_id = request.form.get('modulo_id')
            tipo = request.form.get('tipo', 'Full Time')
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
                    c.execute("INSERT INTO workers (rut, name, phone, password_hash, is_admin, modulo_id, tipo) VALUES (?, ?, ?, ?, 0, ?, ?)", 
                              (rut, name, phone, p_hash, modulo_id, tipo))
                    conn.commit()
                    flash(f"Trabajador guardado. Contraseña temporal: <strong>{password}</strong>", "success")
                    return redirect(url_for('manage_workers')) 
                except sqlite3.IntegrityError:
                    flash("El RUT ya existe en el sistema.", "danger")

        c.execute('''SELECT w.id, w.rut, w.name, w.phone, m.name, w.modulo_id, w.tipo 
                     FROM workers w 
                     LEFT JOIN modulos m ON w.modulo_id = m.id 
                     WHERE w.is_admin = 0''')
        workers = c.fetchall()
        
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
        conn = get_db_connection()
        c = conn.cursor()
        
        if request.method == 'POST':
            raw_phone = request.form['phone']
            name = request.form['name'].strip()
            modulo_id = request.form.get('modulo_id')
            tipo = request.form.get('tipo', 'Full Time')

            if not validate_phone(raw_phone):
                flash("El teléfono debe tener 9 dígitos válidos.", "danger")
                return redirect(url_for('edit_worker', id=id))
            elif not modulo_id:
                flash("Debes seleccionar un módulo.", "danger")
                return redirect(url_for('edit_worker', id=id))

            c.execute("UPDATE workers SET name=?, phone=?, modulo_id=?, tipo=? WHERE id=?", 
                      (name, format_phone(raw_phone), modulo_id, tipo, id))
            conn.commit()
            flash("Trabajador actualizado exitosamente.", "success")
            conn.close()
            return redirect(url_for('manage_workers'))

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
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM workers WHERE id=?", (id,))
        conn.commit()
        conn.close()
        flash("Trabajador eliminado.", "info")
        return redirect(url_for('manage_workers'))

    @app.route('/admin/workers/reset_password/<int:id>', methods=['POST'])
    @admin_required
    def admin_reset_password(id):
        conn = get_db_connection()
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
        conn = get_db_connection()
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

        c.execute("SELECT id, name FROM zonas ORDER BY name")
        zonas = c.fetchall()
        
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
        conn = get_db_connection()
        c = conn.cursor()
        try:
            if type == 'zona':
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
        conn = get_db_connection()
        c = conn.cursor()

        if request.method == 'POST':
            name = request.form.get('name').strip()
            zona_id = request.form.get('zona_id')
            
            raw_price = request.form.get('price').replace('.', '')
            raw_commission = request.form.get('commission').replace('.', '')

            if not zona_id:
                flash("Debes seleccionar una Zona.", "danger")
            else:
                try:
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
        conn = get_db_connection()
        c = conn.cursor()

        if request.method == 'POST':
            name = request.form.get('name').strip()
            zona_id = request.form.get('zona_id')
            
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
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM productos WHERE id=?", (id,))
        conn.commit()
        conn.close()
        flash("Producto eliminado.", "info")
        return redirect(url_for('manage_products'))

    @app.route('/admin/rendiciones')
    @admin_required
    def admin_rendiciones():
        # Capturamos todos los filtros
        mes_seleccionado = request.args.get('mes')
        anio_seleccionado = request.args.get('anio')
        dia_seleccionado = request.args.get('dia')
        zona_id_seleccionada = request.args.get('zona_id')
        modulo_id_seleccionado = request.args.get('modulo_id')
        
        # Si no viene la variable 'mes' en la URL, significa que es la primera vez que entramos
        if request.args.get('mes') is None:
            hoy = date.today()
            mes_seleccionado = f"{hoy.month:02d}"
            anio_seleccionado = str(hoy.year)
            dia_seleccionado = f"{hoy.day:02d}" # <-- Forzamos el día actual
        
        mes_seleccionado = mes_seleccionado.zfill(2)

        conn = get_db_connection()
        c = conn.cursor()
        
        # Construimos la consulta base tipo Lego
        query = '''
            SELECT r.id, r.fecha, w.name, m.name,
                r.venta_debito, r.venta_credito, r.venta_mp, r.venta_efectivo, r.gastos, r.observaciones,
                c_w.name, r.worker_id, r.companion_id, r.modulo_id,
                r.worker_comision, r.companion_comision,
                r.boletas_debito, r.boletas_credito, r.boletas_mp, r.boletas_efectivo
            FROM rendiciones r
            JOIN workers w ON r.worker_id = w.id
            JOIN modulos m ON r.modulo_id = m.id
            LEFT JOIN workers c_w ON r.companion_id = c_w.id
            WHERE strftime('%m', r.fecha) = ? AND strftime('%Y', r.fecha) = ?
        '''
        params = [mes_seleccionado, anio_seleccionado]

        # Añadimos las piezas extra si el usuario las seleccionó
        if dia_seleccionado:
            query += " AND strftime('%d', r.fecha) = ?"
            params.append(dia_seleccionado.zfill(2))
            
        if zona_id_seleccionada:
            query += " AND m.zona_id = ?"
            params.append(zona_id_seleccionada)
            
        if modulo_id_seleccionado:
            query += " AND r.modulo_id = ?"
            params.append(modulo_id_seleccionado)

        query += " ORDER BY r.fecha DESC, r.id DESC"
        
        c.execute(query, tuple(params))
        rendiciones_basicas = c.fetchall()
        
        rendiciones_completas = []
        for r in rendiciones_basicas:
            c.execute('''
                SELECT p.name, ri.cantidad, ri.precio_historico, ri.comision_historica,
                    (ri.cantidad * ri.precio_historico) as total_linea,
                    (ri.cantidad * ri.comision_historica) as total_comision,
                    ri.id
                FROM rendicion_items ri
                JOIN productos p ON ri.producto_id = p.id
                WHERE ri.rendicion_id = ?
            ''', (r[0],))
            items = c.fetchall()

            total_calculado = sum(item[4] for item in items)
            comision_total = sum(item[5] for item in items)
            r_completa = r + (items, total_calculado, comision_total)
            rendiciones_completas.append(r_completa)

        # Cargar catálogos para los selects
        c.execute("SELECT id, name, tipo, modulo_id FROM workers WHERE is_admin = 0 ORDER BY name")
        workers = c.fetchall()
        
        # Ahora traemos el zona_id para poder filtrar los módulos por zona en el frontend
        c.execute("SELECT id, name, zona_id FROM modulos ORDER BY name")
        modulos = c.fetchall()
        
        c.execute("SELECT id, name FROM zonas ORDER BY name")
        zonas = c.fetchall()

        c.execute("SELECT DISTINCT strftime('%Y', fecha) FROM rendiciones ORDER BY 1 DESC")
        anios_db = c.fetchall()
        anios_disponibles = [row[0] for row in anios_db] if anios_db else [str(date.today().year)]
        if str(date.today().year) not in anios_disponibles:
            anios_disponibles.insert(0, str(date.today().year))

        conn.close()
        
        dias_disponibles = [f"{d:02d}" for d in range(1, 32)]

        return render_template('admin_rendiciones.html', 
                               rendiciones=rendiciones_completas,
                               workers=workers,
                               modulos=modulos,
                               zonas=zonas,
                               mes_actual=mes_seleccionado,
                               anio_actual=anio_seleccionado,
                               dia_actual=dia_seleccionado,
                               zona_actual=zona_id_seleccionada,
                               modulo_actual=modulo_id_seleccionado,
                               anios_disponibles=anios_disponibles,
                               dias_disponibles=dias_disponibles)

    @app.route('/admin/rendiciones/delete/<int:id>', methods=['POST'])
    @admin_required
    def delete_rendicion(id):
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("DELETE FROM rendicion_items WHERE rendicion_id=?", (id,))
        c.execute("DELETE FROM rendiciones WHERE id=?", (id,))
        
        conn.commit()
        conn.close()
        
        flash("Rendición eliminada.", "info")
        return redirect(url_for('admin_rendiciones'))


    @app.route('/admin/rendiciones/edit/<int:id>', methods=['POST'])
    @admin_required
    def edit_rendicion(id):
        conn = get_db_connection()
        c = conn.cursor()

        # Obtener datos básicos
        fecha = request.form.get('fecha')
        worker_id = request.form.get('worker_id')
        modulo_id = request.form.get('modulo_id')  # Asegúrate de tener el input hidden en el HTML
        companion_id = request.form.get('companion_id') or None
        if companion_id and worker_id == companion_id:
            flash("Error: No puedes asignarte a ti mismo como acompañante.", "danger")
            return redirect(url_for('admin_rendiciones'))
        worker_comision = 1 if request.form.get('worker_comision') else 0
        companion_comision = 1 if request.form.get('companion_comision') else 0

        # Limpiador de dinero para manejar los puntos de miles
        def clean_money(val):
            if not val: return 0
            return int(str(val).replace('.', '').replace('$', ''))

        try:
            debito = clean_money(request.form.get('venta_debito'))
            credito = clean_money(request.form.get('venta_credito'))
            mp = clean_money(request.form.get('venta_mp'))
            efectivo = clean_money(request.form.get('venta_efectivo'))
            
            bol_debito = int(request.form.get('boletas_debito') or 0)
            bol_credito = int(request.form.get('boletas_credito') or 0)
            bol_mp = int(request.form.get('boletas_mp') or 0)
            bol_efectivo = int(request.form.get('boletas_efectivo') or 0)
            
            gastos = clean_money(request.form.get('gastos'))
            observaciones = request.form.get('observaciones', '').strip()

            # 1. Actualizar cantidades de productos
            # Recorremos el formulario buscando las cantidades editadas
            for key, value in request.form.items():
                if key.startswith('qty_'):
                    # En el modal el name es 'qty_{{ item[6] }}' donde item[6] es el ID de rendicion_items
                    ri_id = key.split('_')[1]
                    nueva_qty = int(value or 0)
                    
                    # IMPORTANTE: Usamos 'precio_historico' que es el nombre real en tu DB
                    c.execute('''UPDATE rendicion_items 
                                SET cantidad = ? 
                                WHERE id = ?''', (nueva_qty, ri_id))

            # 2. Actualizar la rendición principal
            c.execute('''
                UPDATE rendiciones 
                SET fecha=?, worker_id=?, modulo_id=?, companion_id=?,
                    venta_debito=?, venta_credito=?, venta_mp=?, venta_efectivo=?, 
                    boletas_debito=?, boletas_credito=?, boletas_mp=?, boletas_efectivo=?,
                    gastos=?, observaciones=?, worker_comision=?, companion_comision=?
                WHERE id=?
            ''', (fecha, worker_id, modulo_id, companion_id, 
                debito, credito, mp, efectivo, 
                bol_debito, bol_credito, bol_mp, bol_efectivo,
                gastos, observaciones, worker_comision, companion_comision, id))   
            
            conn.commit()
            flash("Rendición y productos actualizados correctamente.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error al actualizar: {str(e)}", "danger")
        finally:
            conn.close()

        return redirect(url_for('admin_rendiciones'))

    @app.route('/admin/reportes')
    @admin_required 
    def admin_reportes_index():
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT m.id, m.name, z.name 
            FROM modulos m
            JOIN zonas z ON m.zona_id = z.id
            ORDER BY z.name, m.name
        ''')
        modulos = c.fetchall()
        conn.close()
        
        return render_template('admin_reportes_index.html', modulos=modulos)

    @app.route('/admin/reportes/modulo/<int:modulo_id>')
    @admin_required
    def report_modulo_periodo(modulo_id):
        mes_actual = date.today().month
        anio_actual = date.today().year
        dias_en_periodo = [f'{d:02}' for d in range(1, 32)] 
        
        conn = get_db_connection()
        c = conn.cursor()

        c.execute("SELECT name FROM modulos WHERE id = ?", (modulo_id,))
        modulo_info = c.fetchone()
        if not modulo_info:
            conn.close()
            flash("Módulo no encontrado.", "danger")
            return redirect(url_for('admin_reportes_index'))
        modulo_name = modulo_info[0]

        c.execute('''
            SELECT strftime('%d', r.fecha) as dia,
                   SUM(r.venta_debito) as debito,
                   SUM(r.venta_credito) as credito,
                   SUM(r.venta_mp) as mp,
                   SUM(r.venta_efectivo) as efectivo,
                   SUM(r.gastos) as gastos
            FROM rendiciones r
            WHERE r.modulo_id = ? AND strftime('%m', r.fecha) = ? AND strftime('%Y', r.fecha) = ?
            GROUP BY dia
        ''', (modulo_id, f'{mes_actual:02}', str(anio_actual)))
        finanzas_db = c.fetchall()

        c.execute('''
            SELECT strftime('%d', r.fecha) as dia,
                   SUM(ri.cantidad * ri.comision_historica * CASE WHEN r.worker_comision = 1 OR r.companion_comision = 1 THEN 1 ELSE 0 END) as comision_total
            FROM rendicion_items ri
            JOIN rendiciones r ON ri.rendicion_id = r.id
            WHERE r.modulo_id = ? AND strftime('%m', r.fecha) = ? AND strftime('%Y', r.fecha) = ?
            GROUP BY dia
        ''', (modulo_id, f'{mes_actual:02}', str(anio_actual)))
        comisiones_db = c.fetchall()
        
        conn.close()

        data_por_dia = {dia: {'debito': 0, 'credito': 0, 'mp': 0, 'efectivo': 0, 'gastos': 0, 'comision': 0, 'venta_total': 0} for dia in dias_en_periodo}

        for row in finanzas_db:
            dia, debito, credito, mp, efectivo, gastos = row
            venta_total = (debito or 0) + (credito or 0) + (mp or 0) + (efectivo or 0)
            data_por_dia[dia].update({
                'debito': debito or 0,
                'credito': credito or 0,
                'mp': mp or 0,
                'efectivo': efectivo or 0,
                'gastos': gastos or 0,
                'venta_total': venta_total
            })

        for row in comisiones_db:
            dia, comision = row
            data_por_dia[dia]['comision'] = comision or 0

        totales_mes = {'debito': 0, 'credito': 0, 'mp': 0, 'efectivo': 0, 'gastos': 0, 'comision': 0, 'venta_total': 0}
        dias_activos = 0
        
        for dia, datos in data_por_dia.items():
            if datos['venta_total'] > 0 or datos['gastos'] > 0:
                dias_activos += 1
            for k in totales_mes.keys():
                totales_mes[k] += datos[k]

        return render_template('admin_report_modulo.html',
                               modulo_name=modulo_name,
                               mes_nombre=f'{mes_actual:02}/{anio_actual}',
                               dias_en_periodo=dias_en_periodo,
                               data_por_dia=data_por_dia,
                               totales_mes=totales_mes,
                               dias_activos=dias_activos)
        
    @app.route('/admin/reportes/modulo/<int:modulo_id>/comisiones')
    @admin_required
    def report_modulo_comisiones(modulo_id):
        mes_actual = date.today().month
        anio_actual = date.today().year
        
        conn = get_db_connection()
        c = conn.cursor()

        c.execute("SELECT name FROM modulos WHERE id = ?", (modulo_id,))
        modulo_info = c.fetchone()
        if not modulo_info:
            conn.close()
            flash("Módulo no encontrado.", "danger")
            return redirect(url_for('admin_reportes_index'))
        modulo_name = modulo_info[0]

        # Fetch rendiciones with commission calculations for this module and month
        c.execute('''
            SELECT r.id, strftime('%d', r.fecha) as dia, 
                   w.id, w.name, w.tipo, r.worker_comision,
                   cw.id, cw.name, cw.tipo, r.companion_comision,
                   COALESCE((SELECT SUM(cantidad * comision_historica) FROM rendicion_items WHERE rendicion_id = r.id), 0) as total_comision
            FROM rendiciones r
            JOIN workers w ON r.worker_id = w.id
            LEFT JOIN workers cw ON r.companion_id = cw.id
            WHERE r.modulo_id = ? AND strftime('%m', r.fecha) = ? AND strftime('%Y', r.fecha) = ?
            ORDER BY r.fecha ASC
        ''', (modulo_id, f'{mes_actual:02}', str(anio_actual)))
        
        rendiciones = c.fetchall()
        conn.close()

        workers_data = {}
        
        for row in rendiciones:
            r_id, dia, w_id, w_name, w_tipo, w_com, c_id, c_name, c_tipo, c_com, total_com = row
            
            w_share = 0
            c_share = 0
            
            # Split logic
            if w_com and c_com:
                w_share = total_com / 2
                c_share = total_com / 2
            elif w_com:
                w_share = total_com
            elif c_com:
                c_share = total_com
                
            # Process Titular Worker
            if w_id not in workers_data:
                workers_data[w_id] = {'name': w_name, 'tipo': w_tipo, 'dias': {}, 'total': 0, 'enabled': bool(w_com)}
            else:
                if w_com: workers_data[w_id]['enabled'] = True
            
            workers_data[w_id]['dias'][dia] = workers_data[w_id]['dias'].get(dia, 0) + w_share
            workers_data[w_id]['total'] += w_share
            
            # Process Companion (if any)
            if c_id:
                if c_id not in workers_data:
                    workers_data[c_id] = {'name': c_name, 'tipo': c_tipo, 'dias': {}, 'total': 0, 'enabled': bool(c_com)}
                else:
                    if c_com: workers_data[c_id]['enabled'] = True
                    
                workers_data[c_id]['dias'][dia] = workers_data[c_id]['dias'].get(dia, 0) + c_share
                workers_data[c_id]['total'] += c_share

        # Sort alphabetically so the table doesn't shuffle randomly
        workers_data = dict(sorted(workers_data.items(), key=lambda item: item[1]['name']))
        dias_en_periodo = [f'{d:02}' for d in range(1, 32)]

        return render_template('admin_report_comisiones.html',
                               modulo_name=modulo_name,
                               mes_nombre=f'{mes_actual:02}/{anio_actual}',
                               workers_data=workers_data,
                               dias_en_periodo=dias_en_periodo)
        
    @app.route('/admin/reportes/modulo/<int:modulo_id>/horarios')
    @admin_required
    def report_modulo_horarios(modulo_id):
        import calendar
        from datetime import date, datetime
        
        mes_actual = date.today().month
        anio_actual = date.today().year
        
        conn = get_db_connection()
        c = conn.cursor()

        c.execute("SELECT name FROM modulos WHERE id = ?", (modulo_id,))
        modulo_info = c.fetchone()
        if not modulo_info:
            conn.close()
            flash("Módulo no encontrado.", "danger")
            return redirect(url_for('admin_reportes_index'))
        modulo_name = modulo_info[0]

        # 1. Pre-cargar a los trabajadores oficiales del módulo (aunque no hayan trabajado aún)
        c.execute("SELECT id, name FROM workers WHERE modulo_id = ? AND is_admin = 0", (modulo_id,))
        assigned_workers = c.fetchall()
        
        workers_data = {}
        for w_id, w_name in assigned_workers:
            workers_data[w_id] = {'name': w_name, 'dias': {}, 'total_horas': 0.0}

        # 2. Extraer rendiciones del mes/módulo
        c.execute('''
            SELECT 
                r.fecha, 
                w.id, w.name, r.hora_entrada, r.hora_salida,
                cw.id, cw.name, r.companion_hora_entrada, r.companion_hora_salida
            FROM rendiciones r
            JOIN workers w ON r.worker_id = w.id
            LEFT JOIN workers cw ON r.companion_id = cw.id
            WHERE r.modulo_id = ? AND strftime('%m', r.fecha) = ? AND strftime('%Y', r.fecha) = ?
            ORDER BY r.fecha ASC
        ''', (modulo_id, f'{mes_actual:02}', str(anio_actual)))
        
        rendiciones = c.fetchall()
        conn.close()

        def calc_horas(in_str, out_str):
            if not in_str or not out_str:
                return 0.0, "0:00"
            try:
                t1 = datetime.strptime(in_str, '%H:%M')
                t2 = datetime.strptime(out_str, '%H:%M')
                delta = t2 - t1
                return delta.seconds / 3600, f"{delta.seconds // 3600}:{(delta.seconds % 3600) // 60:02d}"
            except ValueError:
                return 0.0, "0:00"

        for r in rendiciones:
            fecha, w_id, w_name, w_in, w_out, c_id, c_name, c_in, c_out = r
            dia = fecha[-2:] 
            
            # Titular (Si no es del módulo, lo metemos con etiqueta de Apoyo)
            if w_id not in workers_data:
                workers_data[w_id] = {'name': f"{w_name} (Apoyo)", 'dias': {}, 'total_horas': 0.0}
            
            h_dec, h_str = calc_horas(w_in, w_out)
            workers_data[w_id]['dias'][dia] = {'in': w_in, 'out': w_out, 'hrs': h_str}
            workers_data[w_id]['total_horas'] += h_dec
            
            # Acompañante
            if c_id and c_in and c_out:
                if c_id not in workers_data:
                    workers_data[c_id] = {'name': f"{c_name} (Apoyo)", 'dias': {}, 'total_horas': 0.0}
                
                h_dec, h_str = calc_horas(c_in, c_out)
                workers_data[c_id]['dias'][dia] = {'in': c_in, 'out': c_out, 'hrs': h_str}
                workers_data[c_id]['total_horas'] += h_dec

        for w_id in workers_data:
            th = workers_data[w_id]['total_horas']
            workers_data[w_id]['total_hrs_str'] = f"{int(th)}:{int(round((th - int(th)) * 60)):02d}"

        # Ordenar alfabéticamente (Los de apoyo quedarán entremezclados por orden alfabético)
        workers_data = dict(sorted(workers_data.items(), key=lambda x: x[1]['name']))
        
        _, num_dias = calendar.monthrange(anio_actual, mes_actual)
        nombres_dias = ['D', 'L', 'M', 'M', 'J', 'V', 'S'] # Ajustado para que el 0 de Python(Lunes) sea coherente si usas isoweekday
        
        dias_en_periodo = []
        for d in range(1, num_dias + 1):
            dia_semana = date(anio_actual, mes_actual, d).weekday()
            dias_en_periodo.append({
                'num': f'{d:02}',
                'name': ['L', 'M', 'M', 'J', 'V', 'S', 'D'][dia_semana] # weekday(): Lunes es 0, Domingo es 6
            })

        return render_template('admin_report_horarios.html',
                               modulo_name=modulo_name,
                               mes_nombre=f'{mes_actual:02}/{anio_actual}',
                               workers_data=workers_data,
                               dias_en_periodo=dias_en_periodo)