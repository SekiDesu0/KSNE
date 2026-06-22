from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import aliased
from models.models import db, Rendicion, RendicionItem, Worker, Modulo, Zona, Producto


def get_filter_catalogs():
    workers = db.session.query(
        Worker.id, Worker.name, Worker.tipo, Worker.modulo_id,
    ).filter(Worker.is_admin == False).order_by(Worker.name).all()

    modulos = db.session.query(
        Modulo.id, Modulo.name, Modulo.zona_id,
    ).order_by(Modulo.name).all()

    zonas = db.session.query(Zona.id, Zona.name).order_by(Zona.name).all()

    anios_rows = db.session.query(
        func.strftime('%Y', Rendicion.fecha).label('anio'),
    ).distinct().order_by(func.strftime('%Y', Rendicion.fecha).desc()).all()
    anios_disponibles = [row[0] for row in anios_rows] if anios_rows else [str(date.today().year)]
    if str(date.today().year) not in anios_disponibles:
        anios_disponibles.insert(0, str(date.today().year))

    return workers, modulos, zonas, anios_disponibles


def get_filtered_rendiciones(fecha_inicio, fecha_fin, zona_id, modulo_id):
    from datetime import datetime
    inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()

    Companion = aliased(Worker)

    filters = [
        Rendicion.fecha >= inicio,
        Rendicion.fecha <= fin,
    ]
    if zona_id:
        filters.append(Modulo.zona_id == zona_id)
    if modulo_id:
        filters.append(Rendicion.modulo_id == modulo_id)

    rendiciones = db.session.query(
        Rendicion.id,
        Rendicion.fecha,
        Worker.name.label('worker_name'),
        Modulo.name.label('modulo_name'),
        Rendicion.venta_debito, Rendicion.venta_credito,
        Rendicion.venta_mp, Rendicion.venta_efectivo,
        Rendicion.gastos, Rendicion.observaciones,
        Companion.name.label('companion_name'),
        Rendicion.worker_id, Rendicion.companion_id, Rendicion.modulo_id,
        Rendicion.worker_comision, Rendicion.companion_comision,
        Rendicion.boletas_debito, Rendicion.boletas_credito,
        Rendicion.boletas_mp, Rendicion.boletas_efectivo,
    ).join(Worker, Rendicion.worker_id == Worker.id
    ).join(Modulo, Rendicion.modulo_id == Modulo.id
    ).outerjoin(Companion, Rendicion.companion_id == Companion.id
    ).filter(*filters
    ).order_by(Rendicion.fecha.desc(), Rendicion.id.desc()).all()

    if not rendiciones:
        return []

    rendicion_ids = [r.id for r in rendiciones]
    items_rows = db.session.query(
        Producto.name,
        RendicionItem.cantidad,
        RendicionItem.precio_historico,
        RendicionItem.comision_historica,
        (RendicionItem.cantidad * RendicionItem.precio_historico).label('total_linea'),
        (RendicionItem.cantidad * RendicionItem.comision_historica).label('total_comision'),
        RendicionItem.id,
        RendicionItem.rendicion_id,
    ).join(Producto, RendicionItem.producto_id == Producto.id
    ).filter(RendicionItem.rendicion_id.in_(rendicion_ids)).all()

    items_by_rendicion = {}
    for it in items_rows:
        items_by_rendicion.setdefault(it.rendicion_id, []).append(
            (it[0], it[1], it[2], it[3], it.total_linea, it.total_comision, it.id),
        )

    rendiciones_completas = []
    for r in rendiciones:
        items = items_by_rendicion.get(r.id, [])
        total_calculado = sum(item[4] for item in items)
        comision_total = sum(item[5] for item in items)
        rendiciones_completas.append(tuple(r) + (items, total_calculado, comision_total))

    return rendiciones_completas
