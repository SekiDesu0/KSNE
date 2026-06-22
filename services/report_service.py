import calendar
from datetime import date, datetime
from sqlalchemy import func
from sqlalchemy.orm import aliased
from models.models import db, Modulo, Worker, Rendicion, RendicionItem

Companion = aliased(Worker, name='companion')

WEEKDAY_SHORT = ['L', 'M', 'M', 'J', 'V', 'S', 'D']


def _fecha_filters(anio, mes, dia_f):
    filters = [
        func.strftime('%m', Rendicion.fecha) == mes,
        func.strftime('%Y', Rendicion.fecha) == anio,
    ]
    if dia_f:
        filters.append(func.strftime('%d', Rendicion.fecha) == dia_f.zfill(2))
    return filters


def _dias_en_periodo(anio, mes):
    _, num_dias = calendar.monthrange(int(anio), int(mes))
    return [f'{d:02d}' for d in range(1, num_dias + 1)]


def _dias_con_nombre(anio, mes):
    _, num_dias = calendar.monthrange(int(anio), int(mes))
    return [
        {'num': f'{d:02d}', 'name': WEEKDAY_SHORT[date(int(anio), int(mes), d).weekday()]}
        for d in range(1, num_dias + 1)
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


def get_modulo_periodo_data(modulo_id, anio, mes, dia_f, worker_id):
    filters = [
        Rendicion.modulo_id == modulo_id,
        *_fecha_filters(anio, mes, dia_f),
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

    dias_en_periodo = _dias_en_periodo(anio, mes)
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

    totales_mes = {k: sum(d[k] for d in data_por_dia.values()) for k in data_por_dia['01']}
    dias_activos = sum(1 for d in data_por_dia.values() if d['venta_total'] > 0)

    return {
        'dias_en_periodo': dias_en_periodo,
        'data_por_dia': data_por_dia,
        'totales_mes': totales_mes,
        'dias_activos': dias_activos,
    }


def get_comisiones_data(modulo_id, anio, mes, dia_f, worker_id):
    filters = [
        Rendicion.modulo_id == modulo_id,
        *_fecha_filters(anio, mes, dia_f),
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
        'dias_en_periodo': _dias_en_periodo(anio, mes),
    }


def get_horarios_data(modulo_id, anio, mes, dia_f, worker_id):
    filters = [
        Rendicion.modulo_id == modulo_id,
        *_fecha_filters(anio, mes, dia_f),
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
        'dias_en_periodo': _dias_con_nombre(anio, mes),
    }


def get_cc_data(modulo_id, anio, mes, dia_f, worker_id):
    filters = [
        Rendicion.modulo_id == modulo_id,
        *_fecha_filters(anio, mes, dia_f),
    ]
    if worker_id:
        filters.append(Rendicion.worker_id == worker_id)

    resultados = db.session.query(
        func.strftime('%d', Rendicion.fecha).label('dia'),
        func.sum(Rendicion.boletas_debito + Rendicion.boletas_credito + Rendicion.boletas_mp),
        func.sum(Rendicion.boletas_efectivo),
        func.sum(Rendicion.venta_debito + Rendicion.venta_credito + Rendicion.venta_mp + Rendicion.venta_efectivo),
    ).filter(*filters).group_by('dia').all()

    dias_en_periodo = _dias_en_periodo(anio, mes)
    data_por_dia = {d: {'red_compra': 0, 'efectivo': 0, 'total_trans': 0, 'venta_neta': 0} for d in dias_en_periodo}
    totales = {'red_compra': 0, 'efectivo': 0, 'total_trans': 0, 'venta_neta': 0}

    for r in resultados:
        dia = r[0]
        rc = r[1] or 0
        ef = r[2] or 0
        vt = r[3] or 0
        vn = round(vt / 1.19)
        data_por_dia[dia] = {'red_compra': rc, 'efectivo': ef, 'total_trans': rc + ef, 'venta_neta': vn}
        for k in totales:
            totales[k] += data_por_dia[dia][k]

    return {
        'dias_en_periodo': _dias_con_nombre(anio, mes),
        'data_por_dia': data_por_dia,
        'totales': totales,
    }


def get_iva_data(modulo_id, anio, mes, dia_f, worker_id):
    filters = [
        Rendicion.modulo_id == modulo_id,
        *_fecha_filters(anio, mes, dia_f),
    ]
    if worker_id:
        filters.append(Rendicion.worker_id == worker_id)

    resultados = db.session.query(
        func.strftime('%d', Rendicion.fecha).label('dia'),
        func.sum(Rendicion.venta_efectivo),
        func.sum(Rendicion.venta_debito + Rendicion.venta_credito + Rendicion.venta_mp),
    ).filter(*filters).group_by('dia').all()

    dias_en_periodo = _dias_en_periodo(anio, mes)
    data_por_dia = {d: {'efectivo': 0, 'tbk': 0, 'total': 0, 'porcentaje': 0} for d in dias_en_periodo}
    totales = {'efectivo': 0, 'tbk': 0, 'total': 0, 'porcentaje': 0}

    for r in resultados:
        dia = r[0]
        ef = r[1] or 0
        tbk = r[2] or 0
        tt = ef + tbk
        data_por_dia[dia] = {
            'efectivo': ef, 'tbk': tbk, 'total': tt,
            'porcentaje': round((ef / tt) * 100) if tt > 0 else 0,
        }
        totales['efectivo'] += ef
        totales['tbk'] += tbk
        totales['total'] += tt

    if totales['total'] > 0:
        totales['porcentaje'] = round((totales['efectivo'] / totales['total']) * 100)

    return {
        'dias_en_periodo': _dias_con_nombre(anio, mes),
        'data_por_dia': data_por_dia,
        'totales': totales,
    }
