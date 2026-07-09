from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import date
from database import get_db_connection
from utils import login_required

worker_bp = Blueprint('worker', __name__)

@worker_bp.route('/dashboard')
@login_required
def worker_dashboard():
    conn = get_db_connection()
    c = conn.cursor()

    user_id = session['user_id']

    c.execute('''
        SELECT r.id, r.fecha, w.name, m.name,
            r.venta_debito, r.venta_credito, r.venta_mp, r.venta_efectivo, r.gastos, r.observaciones,
            c_w.name, r.worker_id, r.companion_id, r.modulo_id,
            r.worker_comision, r.companion_comision,
            c_w2.name, r.companion2_id, r.companion2_comision,
            r.boletas_debito, r.boletas_credito, r.boletas_mp, r.boletas_efectivo
        FROM rendiciones r
        JOIN workers w ON r.worker_id = w.id
        JOIN modulos m ON r.modulo_id = m.id
        LEFT JOIN workers c_w ON r.companion_id = c_w.id
        LEFT JOIN workers c_w2 ON r.companion2_id = c_w2.id
        WHERE r.worker_id = ? OR r.companion_id = ?
        ORDER BY r.fecha DESC, r.id DESC
    ''', (user_id, user_id))
    rendiciones_basicas = c.fetchall()

    rendiciones_completas = []
    for r in rendiciones_basicas:
        c.execute('''
            SELECT p.name, ri.cantidad, ri.precio_historico, ri.comision_historica,
                   (ri.cantidad * ri.precio_historico) as total_linea,
                   (ri.cantidad * ri.comision_historica) as total_comision
            FROM rendicion_items ri
            JOIN productos p ON ri.producto_id = p.id
            WHERE ri.rendicion_id = ?
        ''', (r[0],))
        items = c.fetchall()

        total_calculado = sum(item[4] for item in items)
        comision_total = sum(item[5] for item in items)

        rol = "Titular" if r[11] == user_id else "Acompañante"

        r_completa = r + (items, total_calculado, comision_total, rol)
        rendiciones_completas.append(r_completa)

    conn.close()
    return render_template('worker_history.html', rendiciones=rendiciones_completas)

@worker_bp.route('/rendicion/nueva', methods=['GET', 'POST'])
@login_required
def new_rendicion():
    conn = get_db_connection()
    c = conn.cursor()

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

    if request.method == 'POST':
        fecha = request.form.get('fecha')
        hora_entrada = request.form.get('hora_entrada')
        hora_salida = request.form.get('hora_salida')
        companion_hora_entrada = request.form.get('companion_hora_entrada')
        companion_hora_salida = request.form.get('companion_hora_salida')

        def clean_and_validate(val):
            if val is None or val.strip() == "":
                return 0
            try:
                return int(val.replace('.', ''))
            except ValueError:
                return 0

        debito = clean_and_validate(request.form.get('venta_debito'))
        credito = clean_and_validate(request.form.get('venta_credito'))
        mp = clean_and_validate(request.form.get('venta_mp'))
        efectivo = clean_and_validate(request.form.get('venta_efectivo'))
        bol_debito = int(request.form.get('boletas_debito') or 0)
        bol_credito = int(request.form.get('boletas_credito') or 0)
        bol_mp = int(request.form.get('boletas_mp') or 0)
        bol_efectivo = int(request.form.get('boletas_efectivo') or 0)
        gastos = clean_and_validate(request.form.get('gastos')) or 0
        obs = request.form.get('observaciones', '').strip()
        companion_id = request.form.get('companion_id')

        if companion_id == "":
            companion_id = None
            companion_hora_entrada = None
            companion_hora_salida = None

        if debito is None or credito is None or mp is None or efectivo is None or not fecha or not hora_entrada or not hora_salida:
            flash("Error: Todos los campos obligatorios deben estar rellenos.", "danger")
            return redirect(url_for('worker.new_rendicion'))

        c.execute("SELECT tipo FROM workers WHERE id = ?", (session['user_id'],))
        worker_tipo = c.fetchone()[0]
        worker_comision = 1 if worker_tipo == 'Full Time' else 0

        companion_comision = 0
        if companion_id:
            c.execute("SELECT tipo FROM workers WHERE id = ?", (companion_id,))
            comp_tipo = c.fetchone()
            if comp_tipo and comp_tipo[0] == 'Full Time':
                companion_comision = 1

        total_digital = debito + credito + mp
        total_ventas_general = total_digital + efectivo

        c.execute('''INSERT INTO rendiciones
                    (worker_id, companion_id, modulo_id, fecha, hora_entrada, hora_salida, companion_hora_entrada, companion_hora_salida,
                    venta_debito, venta_credito, venta_mp, venta_efectivo, boletas_debito, boletas_credito, boletas_mp, boletas_efectivo, gastos, observaciones, worker_comision, companion_comision)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (session['user_id'], companion_id, modulo_id, fecha, hora_entrada, hora_salida, companion_hora_entrada, companion_hora_salida,
                debito, credito, mp, efectivo, bol_debito, bol_credito, bol_mp, bol_efectivo, gastos, obs, worker_comision, companion_comision))

        rendicion_id = c.lastrowid

        for key, value in request.form.items():
            if key.startswith('qty_') and value and int(value) > 0:
                prod_id = int(key.split('_')[1])
                cantidad = int(value)

                # Buscar el precio vigente al momento de la venta
                c.execute('''
                    SELECT price, commission
                    FROM precios_historicos
                    WHERE producto_id = ? AND zona_id = ?
                    AND fecha_activacion <= datetime('now', 'localtime')
                    ORDER BY fecha_activacion DESC LIMIT 1
                ''', (prod_id, zona_id))
                prod_data = c.fetchone()

                if prod_data:
                    c.execute('''INSERT INTO rendicion_items
                                 (rendicion_id, producto_id, cantidad, precio_historico, comision_historica)
                                 VALUES (?, ?, ?, ?, ?)''',
                              (rendicion_id, prod_id, cantidad, prod_data[0], prod_data[1]))

        conn.commit()
        flash(f"Rendición enviada exitosamente. Total General Declarado: ${total_ventas_general:,}".replace(',', '.'), "success")
        return redirect(url_for('worker.worker_dashboard'))

    c.execute('''
                SELECT id, name FROM workers
                WHERE id != ? AND modulo_id = ? AND is_admin = 0
                ORDER BY name
            ''', (session['user_id'], modulo_id))
    otros_trabajadores = c.fetchall()

    # Buscar solo el precio vigente actual para esta zona
    c.execute('''
        SELECT p.id, p.name, ph.price, ph.commission
        FROM productos p
        JOIN precios_historicos ph ON p.id = ph.producto_id
        WHERE ph.zona_id = ?
          AND ph.fecha_activacion = (
              SELECT MAX(fecha_activacion)
              FROM precios_historicos
              WHERE producto_id = p.id AND zona_id = ?
              AND fecha_activacion <= datetime('now', 'localtime')
          )
        ORDER BY p.name
    ''', (zona_id, zona_id)) # Nota: zona_id se pasa dos veces
    productos = c.fetchall()
    conn.close()

    has_commission = any(prod[3] > 0 for prod in productos)

    return render_template('worker_dashboard.html',
                           modulo_name=modulo_name,
                           zona_name=zona_name,
                           productos=productos,
                           has_commission=has_commission,
                           otros_trabajadores=otros_trabajadores,
                           today=date.today().strftime('%Y-%m-%d'))


@worker_bp.route('/robos-mermas')
@login_required
def historial_robos_mermas():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('''
        SELECT rm.id, rm.fecha, m.name, p.name, rm.cantidad, rm.motivo, rm.observaciones
        FROM robos_mermas rm
        JOIN modulos m ON rm.modulo_id = m.id
        JOIN productos p ON rm.producto_id = p.id
        WHERE rm.worker_id = ?
        ORDER BY rm.fecha DESC, rm.id DESC
    ''', (session['user_id'],))
    reportes = c.fetchall()
    conn.close()

    return render_template('worker_robos_mermas_history.html', reportes=reportes)


@worker_bp.route('/robos-mermas/reportar', methods=['GET', 'POST'])
@login_required
def reportar_robo_merma():
    conn = get_db_connection()
    c = conn.cursor()

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

    if request.method == 'POST':
        fecha = request.form.get('fecha')
        obs_general = request.form.get('observaciones', '').strip()

        if not fecha:
            flash("Error: La fecha es obligatoria.", "danger")
            return redirect(url_for('worker.reportar_robo_merma'))

        items_guardados = 0
        for key, value in request.form.items():
            if key.startswith('qty_') and value and int(value) > 0:
                prod_id = int(key.split('_')[1])
                cantidad = int(value)
                motivo = request.form.get(f'motivo_{prod_id}')

                if motivo in ('robo', 'merma'):
                    c.execute('''INSERT INTO robos_mermas
                                 (worker_id, modulo_id, fecha, producto_id, cantidad, motivo, observaciones)
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
                              (session['user_id'], modulo_id, fecha, prod_id, cantidad, motivo, obs_general))
                    items_guardados += 1

        conn.commit()
        flash(f"Reporte enviado exitosamente. {items_guardados} producto(s) registrado(s).", "success")
        return redirect(url_for('worker.historial_robos_mermas'))

    c.execute('''
        SELECT p.id, p.name, ph.price
        FROM productos p
        JOIN precios_historicos ph ON p.id = ph.producto_id
        WHERE ph.zona_id = ?
          AND ph.fecha_activacion = (
              SELECT MAX(fecha_activacion)
              FROM precios_historicos
              WHERE producto_id = p.id AND zona_id = ?
              AND fecha_activacion <= datetime('now', 'localtime')
          )
        ORDER BY p.name
    ''', (zona_id, zona_id))
    productos = c.fetchall()
    conn.close()

    return render_template('worker_robos_mermas.html',
                           modulo_name=modulo_name,
                           zona_name=zona_name,
                           productos=productos,
                           today=date.today().strftime('%Y-%m-%d'))
