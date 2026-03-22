import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "db/rendiciones.db"

def get_db_connection():
    return sqlite3.connect(DB_NAME)

def populateDefaults():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM zonas")
    if c.fetchone()[0] == 0:
        zonas = ['Norte', 'Quinta', 'RM', 'Sur']
        for zona in zonas:
            c.execute("INSERT INTO zonas (name) VALUES (?)", (zona,))
        c.execute("SELECT id, name FROM zonas")
        zona_map = {name: id for id, name in c.fetchall()}
        modulos_data = [
            ('ANTOFAGASTA', 'Norte'), ('COQUIMBO 1', 'Norte'), ('COQUIMBO 2', 'Norte'),
            ('SERENA 2', 'Norte'), ('SERENA 3', 'Norte'), ('LOS ANDES', 'Quinta'),
            ('VIÑA 1', 'Quinta'), ('VIÑA 2', 'Quinta'), ('CENTRO 2', 'RM'),
            ('IMPERIO 1', 'RM'), ('IMPERIO 2', 'RM'), ('MELIPILLA', 'RM'),
            ('PUENTE ALTO', 'RM'), ('QUILICURA', 'RM'), ('RANCAGUA', 'RM'),
            ('LINARES', 'Sur'), ('SAN FERNANDO', 'Sur'), ('TALCA', 'Sur')
        ]
        for mod_name, zona_name in modulos_data:
            c.execute("INSERT INTO modulos (zona_id, name) VALUES (?, ?)", (zona_map[zona_name], mod_name))
        conn.commit()

    c.execute("SELECT COUNT(*) FROM productos")
    if c.fetchone()[0] == 0:
        productos_data = [
            ('PACK LENTES DE SOL 1 x', 12990, 200),
            ('PACK LENTES DE PANTALLA', 12990, 200),
            ('PACK LENTES DE SOL 2 x', 19990, 400),
            ('PACK LENTES + ESTUCHE BLANDO', 17990, 400),
            ('PACK LENTES + STRAP', 17990, 400),
            ('PACK LENTES 1 x POLARIZADO + ESTUCHE BLANDO+ KIT', 23990, 1000),
            ('PACK LENTES GRANDES ANTIPARRA CON LIGA', 19990, 1000),
            ('ANTIPARRA MEDIANO', 14990, 800),
            ('ANTIPARRA PEQUEÑO', 9990, 200),
            ('PACK LENTES DE GRADUACION', 12990, 200),
            ('PACK LENTES FILTRO AZUL', 14990, 1000),
            ('JOCKEY (2 X PROD. SELECCIONADO)', 9990, 600),
            ('ESTUCHES MODA', 6990, 200),
            ('ESTUCHES CIERRE', 6990, 200),
            ('ESTUCHE DE LECTURA', 6990, 200),
            ('STRAP TELA', 4990, 150),
            ('STRAP DISEÑO', 6990, 200),
            ('STRAP CUERO', 6990, 200),
            ('LIMPIA CRISTAL + PAÑO', 2990, 100),
            ('LENTE LED', 14990, 1000),
            ('PULSERAS', 9990, 200),
            ('SUJETADORES PARA LENTES', 1000, 100),
            ('CORREAS DE CARTERAS DELGADAS Y GRUESAS', 9990, 600),
            ('ESTUCHE COLGANTE DE LENTES', 6990, 200),
            ('COLGANTE DE CELULAR (PULSERA)', 4990, 200),
            ('COLGANTE DE CELULAR (COLLAR)', 6990, 200),
            ('PACK DUO DE COLGANTE DE CELULAR', 7990, 300),
            ('JOCKEY, GORRAS, SOMBREROS, CUELLOS Y OTROS.', 14990, 1000),
            ('CARTERAS ORDENADOR', 9990, 600)
        ]
        c.execute("SELECT id FROM zonas")
        zonas_ids = [row[0] for row in c.fetchall()]
        for zona_id in zonas_ids:
            for name, price, commission in productos_data:
                c.execute("INSERT INTO productos (zona_id, name, price, commission) VALUES (?, ?, ?, ?)", 
                        (zona_id, name, price, commission))

        c.execute("SELECT COUNT(*) FROM workers WHERE is_admin = 0")
        if c.fetchone()[0] == 0:
            c.execute("SELECT id FROM modulos LIMIT 2")
            modulos_ids = c.fetchall()
            if len(modulos_ids) >= 2:
                mod_1 = modulos_ids[0][0]
                mod_2 = modulos_ids[1][0]
                default_pass = generate_password_hash("123456")
                workers_data = [
                    ("11.111.111-1", "Juan Perez", "+56 9 1111 1111", default_pass, 0, mod_1, "Full Time"),
                    ("22.222.222-2", "Maria Gonzalez", "+56 9 2222 2222", default_pass, 0, mod_1, "Part Time"),
                    ("33.333.333-3", "Pedro Soto", "+56 9 3333 3333", default_pass, 0, mod_2, "Full Time"),
                    ("44.444.444-4", "Ana Silva", "+56 9 4444 4444", default_pass, 0, mod_2, "Part Time")
                ]
                for w in workers_data:
                    c.execute("INSERT OR IGNORE INTO workers (rut, name, phone, password_hash, is_admin, modulo_id, tipo) VALUES (?, ?, ?, ?, ?, ?, ?)", w)
                conn.commit()        
    conn.close()

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS zonas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS modulos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  zona_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  FOREIGN KEY (zona_id) REFERENCES zonas(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS productos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  zona_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  price REAL NOT NULL,
                  commission REAL NOT NULL,
                  FOREIGN KEY (zona_id) REFERENCES zonas(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS workers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  rut TEXT UNIQUE NOT NULL,
                  name TEXT NOT NULL,
                  phone TEXT NOT NULL,
                  password_hash TEXT NOT NULL,
                  is_admin BOOLEAN DEFAULT 0,
                  modulo_id INTEGER,
                  tipo TEXT DEFAULT 'Full Time',
                  FOREIGN KEY (modulo_id) REFERENCES modulos(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS rendiciones
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER NOT NULL,
                worker_comision BOOLEAN DEFAULT 1,
                companion_id INTEGER,
                modulo_id INTEGER NOT NULL,
                fecha DATE NOT NULL,
                hora_entrada TEXT NOT NULL,
                hora_salida TEXT NOT NULL,
                companion_hora_entrada TEXT,
                companion_hora_salida TEXT,
                companion_comision BOOLEAN DEFAULT 0,
                venta_debito INTEGER DEFAULT 0,
                venta_credito INTEGER DEFAULT 0,
                venta_mp INTEGER DEFAULT 0,
                venta_efectivo INTEGER DEFAULT 0,
                gastos INTEGER DEFAULT 0,
                observaciones TEXT,
                FOREIGN KEY (worker_id) REFERENCES workers(id),
                FOREIGN KEY (companion_id) REFERENCES workers(id),
                FOREIGN KEY (modulo_id) REFERENCES modulos(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS rendicion_items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  rendicion_id INTEGER NOT NULL,
                  producto_id INTEGER NOT NULL,
                  cantidad INTEGER NOT NULL,
                  precio_historico INTEGER NOT NULL,
                  comision_historica INTEGER NOT NULL,
                  FOREIGN KEY (rendicion_id) REFERENCES rendiciones(id),
                  FOREIGN KEY (producto_id) REFERENCES productos(id))''')
    c.execute("SELECT id FROM workers WHERE is_admin = 1")
    if not c.fetchone():
        admin_pass = generate_password_hash("admin123")
        c.execute("INSERT INTO workers (rut, name, phone, password_hash, is_admin) VALUES (?, ?, ?, ?, ?)", 
                  ("1-9", "System Admin", "+56 9 0000 0000", admin_pass, 1))
    conn.commit()
    conn.close()
    populateDefaults()