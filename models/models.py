from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


_TABLE_ARGS = {'sqlite_autoincrement': True}


class Zona(db.Model):
    __tablename__ = 'zonas'
    __table_args__ = _TABLE_ARGS

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)


class Modulo(db.Model):
    __tablename__ = 'modulos'
    __table_args__ = _TABLE_ARGS

    id = db.Column(db.Integer, primary_key=True)
    zona_id = db.Column(db.Integer, db.ForeignKey('zonas.id'), nullable=False)
    name = db.Column(db.String, nullable=False)


class Producto(db.Model):
    __tablename__ = 'productos'
    __table_args__ = _TABLE_ARGS

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)


class PrecioHistorico(db.Model):
    __tablename__ = 'precios_historicos'
    __table_args__ = _TABLE_ARGS

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    zona_id = db.Column(db.Integer, db.ForeignKey('zonas.id'), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    commission = db.Column(db.Integer, nullable=False)
    fecha_activacion = db.Column(db.DateTime, nullable=False)


class Worker(db.Model):
    __tablename__ = 'workers'
    __table_args__ = _TABLE_ARGS

    id = db.Column(db.Integer, primary_key=True)
    rut = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    modulo_id = db.Column(db.Integer, db.ForeignKey('modulos.id'))
    tipo = db.Column(db.String, default='Full Time')
    nombre_banco = db.Column(db.String, default='')
    numero_cuenta = db.Column(db.String, default='')
    tipo_cuenta = db.Column(db.String, default='')
    rut_banco = db.Column(db.String, default='')


class Rendicion(db.Model):
    __tablename__ = 'rendiciones'
    __table_args__ = _TABLE_ARGS

    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    worker_comision = db.Column(db.Boolean, default=True)
    companion_id = db.Column(db.Integer, db.ForeignKey('workers.id'))
    companion2_id = db.Column(db.Integer, db.ForeignKey('workers.id'))
    modulo_id = db.Column(db.Integer, db.ForeignKey('modulos.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    hora_entrada = db.Column(db.String, nullable=False)
    hora_salida = db.Column(db.String, nullable=False)
    companion_hora_entrada = db.Column(db.String)
    companion_hora_salida = db.Column(db.String)
    companion_comision = db.Column(db.Boolean, default=False)
    companion2_comision = db.Column(db.Boolean, default=False)
    venta_debito = db.Column(db.Integer, default=0)
    venta_credito = db.Column(db.Integer, default=0)
    venta_mp = db.Column(db.Integer, default=0)
    venta_efectivo = db.Column(db.Integer, default=0)
    boletas_debito = db.Column(db.Integer, default=0)
    boletas_credito = db.Column(db.Integer, default=0)
    boletas_mp = db.Column(db.Integer, default=0)
    boletas_efectivo = db.Column(db.Integer, default=0)
    gastos = db.Column(db.Integer, default=0)
    observaciones = db.Column(db.Text)


class RendicionItem(db.Model):
    __tablename__ = 'rendicion_items'
    __table_args__ = _TABLE_ARGS

    id = db.Column(db.Integer, primary_key=True)
    rendicion_id = db.Column(db.Integer, db.ForeignKey('rendiciones.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_historico = db.Column(db.Integer, nullable=False)
    comision_historica = db.Column(db.Integer, nullable=False)
