from datetime import date, datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import aliased
from models.models import db, Modulo, Worker, Rendicion, RendicionItem, RoboMerma, Producto, PrecioHistorico, ProductoComplemento, Complemento, Zona

Companion = aliased(Worker, name='companion')

WEEKDAY_SHORT = ['L', 'M', 'M', 'J', 'V', 'S', 'D']


def _parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').date()


def _fecha_filters(fecha_inicio, fecha_fin):
    filters = [
        Rendicion.fecha >= _parse_date(fecha_inicio),
        Rendicion.fecha <= _parse_date(fecha_fin),
    ]
    return filters


def _dias_en_periodo(fecha_inicio, fecha_fin):
    inicio = _parse_date(fecha_inicio)
    fin = _parse_date(fecha_fin)
    if inicio > fin:
        inicio, fin = fin, inicio
    return [f'{(inicio + timedelta(days=i)).strftime("%d")}' for i in range((fin - inicio).days + 1)]


def _dias_con_nombre(fecha_inicio, fecha_fin):
    inicio = _parse_date(fecha_inicio)
    fin = _parse_date(fecha_fin)
    return [
        {'num': (inicio + timedelta(days=i)).strftime('%d'),
         'name': WEEKDAY_SHORT[(inicio + timedelta(days=i)).weekday()]}
        for i in range((fin - inicio).days + 1)
    ]


def get_modulo_workers_and_anios(modulo_id):
    modulo = db.session.get(Modulo, modulo_id)
    mod_name = modulo.name if modulo else "Módulo"

    workers = db.session.query(Worker.id, Worker.name).filter(
        Worker.modulo_id == modulo_id,
        Worker.is_admin == False,
    ).distinct().order_by(Worker.name).all()
    workers_list = [(w.id, w.name) for w in workers]

    anios_rows = db.session.query(
        func.strftime('%Y', Rendicion.fecha).label('anio'),
    ).distinct().order_by(func.strftime('%Y', Rendicion.fecha).desc()).all()
    anios_list = [row[0] for row in anios_rows]
    if str(date.today().year) not in anios_list:
        anios_list.insert(0, str(date.today().year))

    return mod_name, workers_list, anios_list


def _calcular_horas(hora_in, hora_out):
    if not hora_in or not hora_out:
        return 0, "0:00"
    try:
        t1 = datetime.strptime(hora_in, '%H:%M')
        t2 = datetime.strptime(hora_out, '%H:%M')
        d = t2 - t1
        return d.seconds / 3600, f"{d.seconds // 3600}:{(d.seconds % 3600) // 60:02d}"
    except (ValueError, TypeError):
        return 0, "0:00"


def get_modulo_periodo_data(modulo_id, fecha_inicio, fecha_fin, worker_id):
    filters = [
        Rendicion.modulo_id == modulo_id,
        *_fecha_filters(fecha_inicio, fecha_fin),
    ]
    if worker_id:
        filters.append(Rendicion.worker_id == worker_id)

    finanzas = db.session.query(
        func.strftime('%d', Rendicion.fecha).label('dia'),
        func.sum(Rendicion.venta_debito),
        func.sum(Rendicion.venta_credito),
        func.sum(Rendicion.venta_mp),
        func.sum(Rendicion.venta_efectivo),
        func.sum(Rendicion.gastos),
    ).filter(*filters).group_by('dia').all()

    comision_filters = list(filters) + [
        db.or_(Rendicion.worker_comision == True, Rendicion.companion_comision == True),
    ]
    comisiones_rows = db.session.query(
        func.strftime('%d', Rendicion.fecha).label('dia'),
        func.sum(RendicionItem.cantidad * RendicionItem.comision_historica),
    ).join(Rendicion, RendicionItem.rendicion_id == Rendicion.id).filter(
        *comision_filters,
    ).group_by('dia').all()
    comisiones = {row[0]: row[1] for row in comisiones_rows}

    dias_en_periodo = _dias_en_periodo(fecha_inicio, fecha_fin)
    data_por_dia = {d: {
        'debito': 0, 'credito': 0, 'mp': 0, 'efectivo': 0,
        'gastos': 0, 'comision': 0, 'venta_total': 0,
    } for d in dias_en_periodo}

    for r in finanzas:
        d = r[0]
        debito, credito, mp, efectivo, gastos = (
            r[1] or 0, r[2] or 0, r[3] or 0, r[4] or 0, r[5] or 0,
        )
        vt = debito + credito + mp + efectivo
        data_por_dia[d] = {
            'debito': debito, 'credito': credito, 'mp': mp, 'efectivo': efectivo,
            'gastos': gastos, 'venta_total': vt, 'comision': comisiones.get(d, 0),
        }

    totales_mes = {k: sum(d[k] for d in data_por_dia.values()) for k in (next(iter(data_por_dia.values()), {})).keys()}
    dias_activos = sum(1 for d in data_por_dia.values() if d['venta_total'] > 0)

    return {
        'dias_en_periodo': dias_en_periodo,
        'data_por_dia': data_por_dia,
        'totales_mes': totales_mes,
        'dias_activos': dias_activos,
    }


def get_comisiones_data(modulo_id, fecha_inicio, fecha_fin, worker_id):
    filters = [
        Rendicion.modulo_id == modulo_id,
        *_fecha_filters(fecha_inicio, fecha_fin),
    ]
    if worker_id:
        filters.append(db.or_(Rendicion.worker_id == worker_id, Rendicion.companion_id == worker_id))

    items_subq = db.session.query(
        func.sum(RendicionItem.cantidad * RendicionItem.comision_historica),
    ).filter(RendicionItem.rendicion_id == Rendicion.id).correlate(Rendicion).scalar_subquery()

    rendiciones = db.session.query(
        Rendicion.id,
        func.strftime('%d', Rendicion.fecha).label('dia'),
        Worker.id.label('worker_id'),
        Worker.name.label('worker_name'),
        Worker.tipo.label('worker_tipo'),
        Rendicion.worker_comision,
        Companion.id.label('companion_id'),
        Companion.name.label('companion_name'),
        Companion.tipo.label('companion_tipo'),
        Rendicion.companion_comision,
        items_subq.label('total_com'),
    ).join(Worker, Rendicion.worker_id == Worker.id
    ).outerjoin(Companion, Rendicion.companion_id == Companion.id
    ).filter(*filters).all()

    workers_data = {}
    for r in rendiciones:
        total_com = r.total_com or 0
        for wid, wname, wtipo, wcom in [
            (r.worker_id, r.worker_name, r.worker_tipo, r.worker_comision),
            (r.companion_id, r.companion_name, r.companion_tipo, r.companion_comision),
        ]:
            if wid and wcom:
                if wid not in workers_data:
                    workers_data[wid] = {
                        'name': wname, 'tipo': wtipo, 'dias': {}, 'total': 0, 'enabled': True,
                    }
                val = total_com / 2 if (r.worker_comision and r.companion_comision) else total_com
                workers_data[wid]['dias'][r.dia] = workers_data[wid]['dias'].get(r.dia, 0) + val
                workers_data[wid]['total'] += val

    return {
        'workers_data': dict(sorted(workers_data.items(), key=lambda x: x[1]['name'])),
        'dias_en_periodo': _dias_en_periodo(fecha_inicio, fecha_fin),
    }


def get_horarios_data(modulo_id, fecha_inicio, fecha_fin, worker_id):
    filters = [
        Rendicion.modulo_id == modulo_id,
        *_fecha_filters(fecha_inicio, fecha_fin),
    ]
    if worker_id:
        filters.append(db.or_(Rendicion.worker_id == worker_id, Rendicion.companion_id == worker_id))

    rendiciones = db.session.query(
        Rendicion.fecha,
        Worker.id.label('worker_id'),
        Worker.name.label('worker_name'),
        Rendicion.hora_entrada,
        Rendicion.hora_salida,
        Companion.id.label('companion_id'),
        Companion.name.label('companion_name'),
        Rendicion.companion_hora_entrada,
        Rendicion.companion_hora_salida,
    ).join(Worker, Rendicion.worker_id == Worker.id
    ).outerjoin(Companion, Rendicion.companion_id == Companion.id
    ).filter(*filters).all()

    workers_data = {}
    for r in rendiciones:
        d = r.fecha.strftime('%d')
        for wid, wname, win, wout in [
            (r.worker_id, r.worker_name, r.hora_entrada, r.hora_salida),
            (r.companion_id, r.companion_name, r.companion_hora_entrada, r.companion_hora_salida),
        ]:
            if wid:
                if wid not in workers_data:
                    workers_data[wid] = {'name': wname, 'dias': {}, 'total_horas': 0}
                h_dec, h_str = _calcular_horas(win, wout)
                workers_data[wid]['dias'][d] = {'in': win, 'out': wout, 'hrs': h_str}
                workers_data[wid]['total_horas'] += h_dec

    for w in workers_data.values():
        th = w['total_horas']
        w['total_hrs_str'] = f"{int(th)}:{int((th - int(th)) * 60):02d}"

    return {
        'workers_data': workers_data,
        'dias_en_periodo': _dias_con_nombre(fecha_inicio, fecha_fin),
    }


def get_cc_data(modulo_id, fecha_inicio, fecha_fin, worker_id):
    filters = [
        Rendicion.modulo_id == modulo_id,
        *_fecha_filters(fecha_inicio, fecha_fin),
    ]
    if worker_id:
        filters.append(Rendicion.worker_id == worker_id)

    resultados = db.session.query(
        func.strftime('%d', Rendicion.fecha).label('dia'),
        func.sum(Rendicion.boletas_debito + Rendicion.boletas_credito + Rendicion.boletas_mp),
        func.sum(Rendicion.boletas_efectivo),
        func.sum(Rendicion.venta_debito + Rendicion.venta_credito + Rendicion.venta_mp + Rendicion.venta_efectivo),
    ).filter(*filters).group_by('dia').all()

    dias_en_periodo = _dias_en_periodo(fecha_inicio, fecha_fin)
    data_por_dia = {d: {'red_compra': 0, 'efectivo': 0, 'total_trans': 0, 'venta_neta': 0, 'iva': 0} for d in dias_en_periodo}
    totales = {'red_compra': 0, 'efectivo': 0, 'total_trans': 0, 'venta_neta': 0, 'iva': 0}

    for r in resultados:
        dia = r[0]
        rc = r[1] or 0
        ef = r[2] or 0
        vt = r[3] or 0
        vn = round(vt / 1.19)
        iva = vt - vn
        data_por_dia[dia] = {'red_compra': rc, 'efectivo': ef, 'total_trans': rc + ef, 'venta_neta': vn, 'iva': iva}
        for k in totales:
            totales[k] += data_por_dia[dia][k]

    return {
        'dias_en_periodo': _dias_con_nombre(fecha_inicio, fecha_fin),
        'data_por_dia': data_por_dia,
        'totales': totales,
    }


def get_iva_data(modulo_id, fecha_inicio, fecha_fin, worker_id):
    filters = [
        Rendicion.modulo_id == modulo_id,
        *_fecha_filters(fecha_inicio, fecha_fin),
    ]
    if worker_id:
        filters.append(Rendicion.worker_id == worker_id)

    resultados = db.session.query(
        func.strftime('%d', Rendicion.fecha).label('dia'),
        func.sum(Rendicion.venta_efectivo),
        func.sum(Rendicion.venta_debito),
        func.sum(Rendicion.venta_credito),
        func.sum(Rendicion.venta_mp),
    ).filter(*filters).group_by('dia').all()

    dias_en_periodo = _dias_en_periodo(fecha_inicio, fecha_fin)
    data_por_dia = {d: {'efectivo': 0, 'debito': 0, 'credito': 0, 'mp': 0, 'total': 0,
                        'pct_efectivo': 0, 'pct_debito': 0, 'pct_credito': 0, 'pct_mp': 0} for d in dias_en_periodo}
    totales = {'efectivo': 0, 'debito': 0, 'credito': 0, 'mp': 0, 'total': 0,
               'pct_efectivo': 0, 'pct_debito': 0, 'pct_credito': 0, 'pct_mp': 0}

    for r in resultados:
        dia = r[0]
        ef = r[1] or 0
        deb = r[2] or 0
        cred = r[3] or 0
        mp = r[4] or 0
        tt = ef + deb + cred + mp
        data_por_dia[dia] = {
            'efectivo': ef, 'debito': deb, 'credito': cred, 'mp': mp, 'total': tt,
            'pct_efectivo': round(ef / tt * 100) if tt > 0 else 0,
            'pct_debito': round(deb / tt * 100) if tt > 0 else 0,
            'pct_credito': round(cred / tt * 100) if tt > 0 else 0,
            'pct_mp': round(mp / tt * 100) if tt > 0 else 0,
        }
        for k in ('efectivo', 'debito', 'credito', 'mp', 'total'):
            totales[k] += data_por_dia[dia][k]

    if totales['total'] > 0:
        totales['pct_efectivo'] = round(totales['efectivo'] / totales['total'] * 100)
        totales['pct_debito'] = round(totales['debito'] / totales['total'] * 100)
        totales['pct_credito'] = round(totales['credito'] / totales['total'] * 100)
        totales['pct_mp'] = round(totales['mp'] / totales['total'] * 100)

    return {
        'dias_en_periodo': _dias_con_nombre(fecha_inicio, fecha_fin),
        'data_por_dia': data_por_dia,
        'totales': totales,
    }


def get_robos_mermas_data(modulo_id, fecha_inicio, fecha_fin, worker_id):
    filters = [
        RoboMerma.modulo_id == modulo_id,
        RoboMerma.fecha >= _parse_date(fecha_inicio),
        RoboMerma.fecha <= _parse_date(fecha_fin),
    ]
    if worker_id:
        filters.append(RoboMerma.worker_id == worker_id)

    resultados = db.session.query(
        RoboMerma.producto_id,
        Producto.name,
        RoboMerma.motivo,
        func.sum(RoboMerma.cantidad),
    ).join(Producto, RoboMerma.producto_id == Producto.id
    ).filter(*filters
    ).group_by(RoboMerma.producto_id, RoboMerma.motivo
    ).order_by(Producto.name
    ).all()

    modulo = db.session.get(Modulo, modulo_id)
    zona_id = modulo.zona_id if modulo else None

    precios = {}
    if zona_id:
        precios_rows = db.session.query(
            Producto.id, PrecioHistorico.price
        ).join(PrecioHistorico, Producto.id == PrecioHistorico.producto_id
        ).filter(
            PrecioHistorico.zona_id == zona_id,
            PrecioHistorico.fecha_activacion <= func.datetime('now', 'localtime'),
        ).order_by(
            Producto.id, PrecioHistorico.fecha_activacion.desc()
        ).all()

        seen = set()
        for prod_id, price in precios_rows:
            if prod_id not in seen:
                precios[prod_id] = price
                seen.add(prod_id)

    productos_data = {}
    for prod_id, prod_name, motivo, cantidad in resultados:
        if prod_id not in productos_data:
            productos_data[prod_id] = {
                'name': prod_name,
                'cant_robos': 0, 'cant_mermas': 0,
                'val_robos': 0, 'val_mermas': 0,
                'precio': precios.get(prod_id, 0),
            }
        precio = precios.get(prod_id, 0)
        if motivo == 'robo':
            productos_data[prod_id]['cant_robos'] += cantidad
            productos_data[prod_id]['val_robos'] += cantidad * precio
        else:
            productos_data[prod_id]['cant_mermas'] += cantidad
            productos_data[prod_id]['val_mermas'] += cantidad * precio

    totales = {
        'cant_robos': 0, 'cant_mermas': 0,
        'val_robos': 0, 'val_mermas': 0,
        'cant_total': 0, 'val_total': 0,
    }
    for p in productos_data.values():
        p['cant_total'] = p['cant_robos'] + p['cant_mermas']
        p['val_total'] = p['val_robos'] + p['val_mermas']
        totales['cant_robos'] += p['cant_robos']
        totales['cant_mermas'] += p['cant_mermas']
        totales['val_robos'] += p['val_robos']
        totales['val_mermas'] += p['val_mermas']
        totales['cant_total'] += p['cant_total']
        totales['val_total'] += p['val_total']

    return {
        'productos': productos_data,
        'totales': totales,
    }


def get_productos_vendidos_data(modulo_id, fecha_inicio, fecha_fin, worker_id=None):
    """
    Calcula el total de egresos de productos y complementos.
    Fuentes: ventas (rendicion_items), complementos entregados, robos/mermas.
    """
    # Filtros base para rendiciones
    rend_filters = [
        Rendicion.modulo_id == modulo_id,
        *_fecha_filters(fecha_inicio, fecha_fin),
    ]
    if worker_id:
        rend_filters.append(Rendicion.worker_id == worker_id)

    # Filtros para robos/mermas
    robo_filters = [
        RoboMerma.modulo_id == modulo_id,
        RoboMerma.fecha >= _parse_date(fecha_inicio),
        RoboMerma.fecha <= _parse_date(fecha_fin),
    ]
    if worker_id:
        robo_filters.append(RoboMerma.worker_id == worker_id)

    # Obtener precios actuales de productos
    modulo = db.session.get(Modulo, modulo_id)
    zona_id = modulo.zona_id if modulo else None
    precios = {}
    if zona_id:
        precios_rows = db.session.query(
            Producto.id, PrecioHistorico.price
        ).join(PrecioHistorico, Producto.id == PrecioHistorico.producto_id
        ).filter(
            PrecioHistorico.zona_id == zona_id,
            PrecioHistorico.fecha_activacion <= func.datetime('now', 'localtime'),
        ).order_by(
            Producto.id, PrecioHistorico.fecha_activacion.desc()
        ).all()
        seen = set()
        for prod_id, price in precios_rows:
            if prod_id not in seen:
                precios[prod_id] = price
                seen.add(prod_id)

    # Diccionario para almacenar todos los items
    items = {}

    # FUENTE A: Productos vendidos
    vendidos_query = db.session.query(
        RendicionItem.producto_id,
        Producto.name,
        func.sum(RendicionItem.cantidad).label('total_qty'),
        func.sum(RendicionItem.cantidad * RendicionItem.precio_historico).label('total_valor'),
    ).join(Producto, RendicionItem.producto_id == Producto.id
    ).join(Rendicion, RendicionItem.rendicion_id == Rendicion.id
    ).filter(*rend_filters
    ).group_by(RendicionItem.producto_id, Producto.name
    ).all()

    for prod_id, prod_name, qty, valor in vendidos_query:
        key = ('prod', prod_id)
        if key not in items:
            items[key] = {
                'name': prod_name,
                'tipo': 'Producto',
                'vendidos_qty': 0, 'vendidos_valor': 0,
                'complementos_qty': 0, 'complementos_valor': 0,
                'robos_qty': 0, 'robos_valor': 0,
                'total_qty': 0, 'total_valor': 0,
            }
        items[key]['vendidos_qty'] += qty or 0
        items[key]['vendidos_valor'] += valor or 0

    # FUENTE B: Complementos entregados
    # Por cada rendicion_item vendido, calcular cuántos complementos se entregaron
    complementos_query = db.session.query(
        Complemento.id,
        Complemento.name,
        func.sum(RendicionItem.cantidad * ProductoComplemento.cantidad).label('total_qty'),
    ).join(ProductoComplemento, ProductoComplemento.complemento_id == Complemento.id
    ).join(RendicionItem, RendicionItem.producto_id == ProductoComplemento.producto_id
    ).join(Rendicion, RendicionItem.rendicion_id == Rendicion.id
    ).filter(*rend_filters
    ).group_by(Complemento.id, Complemento.name
    ).all()

    for comp_id, comp_name, qty in complementos_query:
        key = ('comp', comp_id)
        if key not in items:
            items[key] = {
                'name': comp_name,
                'tipo': 'Complemento',
                'vendidos_qty': 0, 'vendidos_valor': 0,
                'complementos_qty': 0, 'complementos_valor': 0,
                'robos_qty': 0, 'robos_valor': 0,
                'total_qty': 0, 'total_valor': 0,
            }
        items[key]['complementos_qty'] += qty or 0
        items[key]['complementos_valor'] = 0  # Complementos valor = $0

    # FUENTE C: Robos/Mermas
    robos_query = db.session.query(
        RoboMerma.producto_id,
        Producto.name,
        RoboMerma.motivo,
        func.sum(RoboMerma.cantidad),
    ).join(Producto, RoboMerma.producto_id == Producto.id
    ).filter(*robo_filters
    ).group_by(RoboMerma.producto_id, RoboMerma.motivo, Producto.name
    ).all()

    for prod_id, prod_name, motivo, cantidad in robos_query:
        key = ('prod', prod_id)
        if key not in items:
            items[key] = {
                'name': prod_name,
                'tipo': 'Producto',
                'vendidos_qty': 0, 'vendidos_valor': 0,
                'complementos_qty': 0, 'complementos_valor': 0,
                'robos_qty': 0, 'robos_valor': 0,
                'total_qty': 0, 'total_valor': 0,
            }
        precio = precios.get(prod_id, 0)
        if motivo == 'robo':
            items[key]['robos_qty'] += cantidad
            items[key]['robos_valor'] += cantidad * precio
        else:  # merma
            items[key]['robos_qty'] += cantidad
            items[key]['robos_valor'] += cantidad * precio

    # Calcular totales por item
    for item in items.values():
        item['total_qty'] = item['vendidos_qty'] + item['complementos_qty'] + item['robos_qty']
        item['total_valor'] = item['vendidos_valor'] + item['complementos_valor'] + item['robos_valor']

    # Ordenar por nombre
    items_sorted = sorted(items.values(), key=lambda x: x['name'])

    # Calcular totales generales
    totales = {
        'vendidos_qty': 0, 'vendidos_valor': 0,
        'complementos_qty': 0, 'complementos_valor': 0,
        'robos_qty': 0, 'robos_valor': 0,
        'total_qty': 0, 'total_valor': 0,
    }
    for item in items_sorted:
        totales['vendidos_qty'] += item['vendidos_qty']
        totales['vendidos_valor'] += item['vendidos_valor']
        totales['complementos_qty'] += item['complementos_qty']
        totales['complementos_valor'] += item['complementos_valor']
        totales['robos_qty'] += item['robos_qty']
        totales['robos_valor'] += item['robos_valor']
        totales['total_qty'] += item['total_qty']
        totales['total_valor'] += item['total_valor']

    return {
        'items': items_sorted,
        'totales': totales,
    }


def get_global_consolidado_data(fecha_inicio, fecha_fin, zona_id=None):
    base_filters = [*_fecha_filters(fecha_inicio, fecha_fin)]
    if zona_id:
        base_filters.append(Modulo.zona_id == zona_id)

    ventas_por_zona_rows = db.session.query(
        Zona.name,
        func.sum(Rendicion.venta_debito + Rendicion.venta_credito + Rendicion.venta_mp + Rendicion.venta_efectivo),
    ).join(Modulo, Rendicion.modulo_id == Modulo.id
    ).join(Zona, Modulo.zona_id == Zona.id
    ).filter(*base_filters
    ).group_by(Zona.name
    ).all()
    ventas_por_zona = {r[0]: (r[1] or 0) for r in ventas_por_zona_rows}

    medios_raw = db.session.query(
        func.sum(Rendicion.venta_efectivo),
        func.sum(Rendicion.venta_debito),
        func.sum(Rendicion.venta_credito),
        func.sum(Rendicion.venta_mp),
    ).join(Modulo, Rendicion.modulo_id == Modulo.id
    ).filter(*base_filters
    ).first()
    medios_pago = {
        'Efectivo': medios_raw[0] or 0,
        'Débito': medios_raw[1] or 0,
        'Crédito': medios_raw[2] or 0,
        'Mercado Pago': medios_raw[3] or 0,
    }

    ventas_diarias_rows = db.session.query(
        func.strftime('%Y-%m-%d', Rendicion.fecha).label('fecha'),
        func.sum(Rendicion.venta_debito + Rendicion.venta_credito + Rendicion.venta_mp + Rendicion.venta_efectivo),
    ).join(Modulo, Rendicion.modulo_id == Modulo.id
    ).filter(*base_filters
    ).group_by('fecha'
    ).order_by('fecha'
    ).all()
    ventas_diarias = [{'fecha': r[0], 'total': r[1] or 0} for r in ventas_diarias_rows]

    top_modulos_rows = db.session.query(
        Modulo.name,
        Zona.name,
        func.sum(Rendicion.venta_debito + Rendicion.venta_credito + Rendicion.venta_mp + Rendicion.venta_efectivo),
        func.sum(Rendicion.gastos),
    ).join(Modulo, Rendicion.modulo_id == Modulo.id
    ).join(Zona, Modulo.zona_id == Zona.id
    ).filter(*base_filters
    ).group_by(Modulo.id, Modulo.name, Zona.name
    ).order_by(func.sum(Rendicion.venta_debito + Rendicion.venta_credito + Rendicion.venta_mp + Rendicion.venta_efectivo).desc()
    ).limit(10
    ).all()
    top_modulos = [
        {'modulo': r[0], 'zona': r[1], 'ventas': r[2] or 0, 'gastos': r[3] or 0}
        for r in top_modulos_rows
    ]

    comision_filters = list(base_filters) + [
        db.or_(Rendicion.worker_comision == True, Rendicion.companion_comision == True),
    ]
    comisiones_total = db.session.query(
        func.sum(RendicionItem.cantidad * RendicionItem.comision_historica),
    ).join(Rendicion, RendicionItem.rendicion_id == Rendicion.id
    ).join(Modulo, Rendicion.modulo_id == Modulo.id
    ).filter(*comision_filters
    ).scalar() or 0

    gastos_total = db.session.query(
        func.sum(Rendicion.gastos),
    ).join(Modulo, Rendicion.modulo_id == Modulo.id
    ).filter(*base_filters
    ).scalar() or 0

    dias_activos = db.session.query(
        func.count(func.distinct(Rendicion.fecha)),
    ).join(Modulo, Rendicion.modulo_id == Modulo.id
    ).filter(*base_filters
    ).scalar() or 0

    zonas = db.session.query(Zona.id, Zona.name).order_by(Zona.name).all()
    zonas_list = [(z.id, z.name) for z in zonas]

    total_ventas = sum(ventas_por_zona.values())

    return {
        'ventas_por_zona': ventas_por_zona,
        'medios_pago': medios_pago,
        'ventas_diarias': ventas_diarias,
        'top_modulos': top_modulos,
        'totales': {
            'ventas': total_ventas,
            'comisiones': comisiones_total,
            'gastos': gastos_total,
            'dias_activos': dias_activos,
        },
        'zonas': zonas_list,
    }


def get_metas_data(anio, mes, porcentaje):
    import calendar
    hoy = date.today()
    dias_del_mes = calendar.monthrange(anio, mes)[1]

    if anio == hoy.year and mes == hoy.month:
        dias_transcurridos = hoy.day
    else:
        dias_transcurridos = dias_del_mes

    mes_inicio = date(anio, mes, 1)
    mes_fin = date(anio, mes, dias_del_mes)
    ly_anio = anio - 1
    ly_inicio = date(ly_anio, mes, 1)
    ly_fin = date(ly_anio, mes, dias_del_mes)

    factor = 1 + porcentaje / 100.0

    modulos_rows = db.session.query(Modulo.id, Modulo.name, Zona.name).join(
        Zona, Modulo.zona_id == Zona.id
    ).order_by(Zona.name, Modulo.name).all()

    last_year_sales = {}
    ly_rows = db.session.query(
        Rendicion.modulo_id,
        func.sum(Rendicion.venta_debito + Rendicion.venta_credito + Rendicion.venta_mp + Rendicion.venta_efectivo),
    ).filter(
        Rendicion.fecha >= ly_inicio,
        Rendicion.fecha <= ly_fin,
    ).group_by(Rendicion.modulo_id).all()
    for r in ly_rows:
        last_year_sales[r[0]] = r[1] or 0

    current_sales = {}
    cur_rows = db.session.query(
        Rendicion.modulo_id,
        func.sum(Rendicion.venta_debito + Rendicion.venta_credito + Rendicion.venta_mp + Rendicion.venta_efectivo),
    ).filter(
        Rendicion.fecha >= mes_inicio,
        Rendicion.fecha <= mes_fin,
    ).group_by(Rendicion.modulo_id).all()
    for r in cur_rows:
        current_sales[r[0]] = r[1] or 0

    rows = []
    total_meta = 0
    total_ventas = 0
    modulos_cumplen = 0

    for mod_id, mod_name, zona_name in modulos_rows:
        ventas_ly = last_year_sales.get(mod_id, 0)
        meta_total = round(ventas_ly * factor)
        ventas = current_sales.get(mod_id, 0)

        if meta_total > 0:
            pct_cumplimiento = round(ventas / meta_total * 100, 2)
            desfase = round(100 - pct_cumplimiento, 2)
        else:
            pct_cumplimiento = 0.0
            desfase = 0.0

        if dias_transcurridos > 0:
            meta_al_dia = round(meta_total * dias_transcurridos / dias_del_mes)
        else:
            meta_al_dia = 0

        diferencia = ventas - meta_al_dia

        if dias_transcurridos > 0:
            proyeccion = round(ventas / dias_transcurridos * dias_del_mes)
        else:
            proyeccion = 0

        if meta_total > 0:
            pct_proyeccion = round(proyeccion / meta_total * 100, 2)
        else:
            pct_proyeccion = 0.0

        cumple = ventas >= meta_total
        if cumple:
            modulos_cumplen += 1

        total_meta += meta_total
        total_ventas += ventas

        rows.append({
            'zona': zona_name,
            'modulo': mod_name,
            'meta_total': meta_total,
            'ventas': ventas,
            'pct_cumplimiento': pct_cumplimiento,
            'desfase': desfase,
            'meta_al_dia': meta_al_dia,
            'diferencia': diferencia,
            'proyeccion': proyeccion,
            'pct_proyeccion': pct_proyeccion,
            'cumple': cumple,
        })

    if total_meta > 0:
        total_pct = round(total_ventas / total_meta * 100, 2)
        total_desfase = round(100 - total_pct, 2)
    else:
        total_pct = 0.0
        total_desfase = 0.0

    if dias_del_mes > 0:
        total_meta_al_dia = round(total_meta * dias_transcurridos / dias_del_mes)
    else:
        total_meta_al_dia = 0

    total_diferencia = total_ventas - total_meta_al_dia

    if dias_transcurridos > 0:
        total_proyeccion = round(total_ventas / dias_transcurridos * dias_del_mes)
    else:
        total_proyeccion = 0

    if total_meta > 0:
        total_pct_proyeccion = round(total_proyeccion / total_meta * 100, 2)
    else:
        total_pct_proyeccion = 0

    pct_mes = round(dias_transcurridos / dias_del_mes * 100, 2)
    meta_cumplida = total_ventas >= total_meta

    return {
        'rows': rows,
        'totales': {
            'meta': total_meta,
            'ventas': total_ventas,
            'pct_cumplimiento': total_pct,
            'desfase': total_desfase,
            'meta_al_dia': total_meta_al_dia,
            'diferencia': total_diferencia,
            'proyeccion': total_proyeccion,
            'pct_proyeccion': total_pct_proyeccion,
        },
        'summary': {
            'dias_del_mes': dias_del_mes,
            'dias_transcurridos': dias_transcurridos,
            'pct_mes': pct_mes,
            'meta_cumplida': meta_cumplida,
            'modulos_cumplen': modulos_cumplen,
            'total_modulos': len(modulos_rows),
        },
    }
