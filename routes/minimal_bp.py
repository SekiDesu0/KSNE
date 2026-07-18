from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import date
from sqlalchemy import func
from werkzeug.security import check_password_hash

from models.models import db, Worker, Modulo, Zona, Producto, PrecioHistorico, Rendicion, RendicionItem, RoboMerma
from services import rendiciones_service
from utils import login_required, validate_rut, format_rut

minimal_bp = Blueprint('minimal', __name__, url_prefix='/minimal')


@minimal_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin.admin_rendiciones'))
        return redirect(url_for('minimal.index'))

    if request.method == 'POST':
        raw_rut = request.form['rut']
        password = request.form['password']
        rut = format_rut(raw_rut) if validate_rut(raw_rut) else raw_rut
        user = Worker.query.filter_by(rut=rut).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            session['rut'] = rut
            session['worker_name'] = user.name
            if user.is_admin:
                return redirect(url_for('admin.admin_rendiciones'))
            return redirect(url_for('minimal.index'))
        else:
            flash("RUT o contraseña incorrectos.", "danger")

    return render_template('minimal/login.html')


@minimal_bp.route('/')
@login_required
def index():
    user_id = session['user_id']
    rendiciones = rendiciones_service.get_worker_rendiciones(user_id)
    rendicion_ids = [r[0] for r in rendiciones]
    time_rows = db.session.query(
        Rendicion.id, Rendicion.hora_entrada, Rendicion.hora_salida,
        Rendicion.companion_hora_entrada, Rendicion.companion_hora_salida
    ).filter(Rendicion.id.in_(rendicion_ids)).all()
    times = {t.id: (t.hora_entrada, t.hora_salida, t.companion_hora_entrada, t.companion_hora_salida) for t in time_rows}
    return render_template('minimal/history.html', rendiciones=rendiciones, times=times)


@minimal_bp.route('/rendicion/nueva', methods=['GET', 'POST'])
@login_required
def new_rendicion():
    user_id = session['user_id']
    worker = Worker.query.get(user_id)
    modulo = Modulo.query.get(worker.modulo_id)
    zona = Zona.query.get(modulo.zona_id)

    if not worker or not modulo:
        return "Error: No tienes un módulo asignado. Contacta al administrador."

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

        if not all([debito is not None, credito is not None, mp is not None, efectivo is not None,
                    fecha, hora_entrada, hora_salida]):
            flash("Error: Todos los campos obligatorios deben estar rellenos.", "danger")
            return redirect(url_for('minimal.new_rendicion'))

        worker_comision = 1 if worker.tipo == 'Full Time' else 0

        companion_comision = 0
        if companion_id:
            companion = Worker.query.get(companion_id)
            if companion and companion.tipo == 'Full Time':
                companion_comision = 1

        total_digital = debito + credito + mp
        total_ventas_general = total_digital + efectivo

        rendicion = Rendicion(
            worker_id=user_id,
            companion_id=int(companion_id) if companion_id else None,
            modulo_id=worker.modulo_id,
            fecha=date.fromisoformat(fecha),
            hora_entrada=hora_entrada,
            hora_salida=hora_salida,
            companion_hora_entrada=companion_hora_entrada or None,
            companion_hora_salida=companion_hora_salida or None,
            venta_debito=debito,
            venta_credito=credito,
            venta_mp=mp,
            venta_efectivo=efectivo,
            boletas_debito=bol_debito,
            boletas_credito=bol_credito,
            boletas_mp=bol_mp,
            boletas_efectivo=bol_efectivo,
            gastos=gastos,
            observaciones=obs,
            worker_comision=bool(worker_comision),
            companion_comision=bool(companion_comision),
        )
        db.session.add(rendicion)
        db.session.flush()

        for key, value in request.form.items():
            if key.startswith('qty_') and value and int(value) > 0:
                prod_id = int(key.split('_')[1])
                cantidad = int(value)

                ph = PrecioHistorico.query.filter(
                    PrecioHistorico.producto_id == prod_id,
                    PrecioHistorico.zona_id == zona.id,
                    PrecioHistorico.fecha_activacion <= func.now(),
                ).order_by(PrecioHistorico.fecha_activacion.desc()).first()

                if ph:
                    db.session.add(RendicionItem(
                        rendicion_id=rendicion.id,
                        producto_id=prod_id,
                        cantidad=cantidad,
                        precio_historico=ph.price,
                        comision_historica=ph.commission,
                    ))

        db.session.commit()
        flash(f"Rendición enviada exitosamente. Total General Declarado: ${total_ventas_general:,}".replace(',', '.'), "success")
        return redirect(url_for('minimal.index'))

    otros_trabajadores = Worker.query.filter(
        Worker.id != user_id,
        Worker.modulo_id == worker.modulo_id,
        Worker.is_admin == False,
    ).order_by(Worker.name).all()
    otros = [(w.id, w.name) for w in otros_trabajadores]

    latest_prices = db.session.query(
        PrecioHistorico.producto_id,
        func.max(PrecioHistorico.fecha_activacion).label('max_fecha'),
    ).filter(
        PrecioHistorico.zona_id == zona.id,
        PrecioHistorico.fecha_activacion <= func.now(),
    ).group_by(PrecioHistorico.producto_id).subquery()

    productos_rows = db.session.query(
        Producto.id, Producto.name, PrecioHistorico.price, PrecioHistorico.commission,
    ).join(PrecioHistorico, Producto.id == PrecioHistorico.producto_id).join(
        latest_prices,
        db.and_(
            PrecioHistorico.producto_id == latest_prices.c.producto_id,
            PrecioHistorico.fecha_activacion == latest_prices.c.max_fecha,
            PrecioHistorico.zona_id == zona.id,
        )
    ).order_by(Producto.name).all()
    productos = [(p.id, p.name, p.price, p.commission) for p in productos_rows]

    has_commission = any(p[3] > 0 for p in productos)

    return render_template('minimal/new_rendicion.html',
                           modulo_name=modulo.name,
                           zona_name=zona.name,
                           productos=productos,
                           has_commission=has_commission,
                           otros_trabajadores=otros,
                           today=date.today().strftime('%Y-%m-%d'))


@minimal_bp.route('/robos-mermas')
@login_required
def robos_mermas():
    user_id = session['user_id']
    reportes_rows = db.session.query(
        RoboMerma.id, RoboMerma.fecha, Modulo.name,
        Producto.name, RoboMerma.cantidad, RoboMerma.motivo, RoboMerma.observaciones,
    ).join(Modulo, RoboMerma.modulo_id == Modulo.id
    ).join(Producto, RoboMerma.producto_id == Producto.id
    ).filter(RoboMerma.worker_id == user_id
    ).order_by(RoboMerma.fecha.desc(), RoboMerma.id.desc()).all()

    reportes = [tuple(r) for r in reportes_rows]
    return render_template('minimal/robos_mermas_history.html', reportes=reportes)


@minimal_bp.route('/robos-mermas/reportar', methods=['GET', 'POST'])
@login_required
def reportar_robo_merma():
    user_id = session['user_id']
    worker = Worker.query.get(user_id)
    modulo = Modulo.query.get(worker.modulo_id)
    zona = Zona.query.get(modulo.zona_id)

    if not worker or not modulo:
        return "Error: No tienes un módulo asignado. Contacta al administrador."

    if request.method == 'POST':
        fecha = request.form.get('fecha')
        obs_general = request.form.get('observaciones', '').strip()

        if not fecha:
            flash("Error: La fecha es obligatoria.", "danger")
            return redirect(url_for('minimal.reportar_robo_merma'))

        items_guardados = 0
        for key, value in request.form.items():
            if key.startswith('qty_') and value and int(value) > 0:
                prod_id = int(key.split('_')[1])
                cantidad = int(value)
                motivo = request.form.get(f'motivo_{prod_id}')

                if motivo in ('robo', 'merma'):
                    db.session.add(RoboMerma(
                        worker_id=user_id,
                        modulo_id=worker.modulo_id,
                        fecha=date.fromisoformat(fecha),
                        producto_id=prod_id,
                        cantidad=cantidad,
                        motivo=motivo,
                        observaciones=obs_general,
                    ))
                    items_guardados += 1

        db.session.commit()
        flash(f"Reporte enviado exitosamente. {items_guardados} producto(s) registrado(s).", "success")
        return redirect(url_for('minimal.robos_mermas'))

    latest_prices = db.session.query(
        PrecioHistorico.producto_id,
        func.max(PrecioHistorico.fecha_activacion).label('max_fecha'),
    ).filter(
        PrecioHistorico.zona_id == zona.id,
        PrecioHistorico.fecha_activacion <= func.now(),
    ).group_by(PrecioHistorico.producto_id).subquery()

    productos_rows = db.session.query(
        Producto.id, Producto.name, PrecioHistorico.price,
    ).join(PrecioHistorico, Producto.id == PrecioHistorico.producto_id).join(
        latest_prices,
        db.and_(
            PrecioHistorico.producto_id == latest_prices.c.producto_id,
            PrecioHistorico.fecha_activacion == latest_prices.c.max_fecha,
            PrecioHistorico.zona_id == zona.id,
        )
    ).order_by(Producto.name).all()
    productos = [(p.id, p.name, p.price) for p in productos_rows]

    return render_template('minimal/reportar_robo_merma.html',
                           modulo_name=modulo.name,
                           zona_name=zona.name,
                           productos=productos,
                           today=date.today().strftime('%Y-%m-%d'))


@minimal_bp.route('/pos')
@login_required
def pos():
    return render_template('minimal/pos.html')


@minimal_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('minimal.login'))
