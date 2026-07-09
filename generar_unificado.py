import random
from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from database import get_db_connection, init_db

def generar_historico_definitivo(dias_atras=1460): # 4 años de datos históricos
    init_db()
    conn = get_db_connection()
    c = conn.cursor()

    # 1. LIMPIEZA TOTAL (Evita el choque con los datos por defecto de database.py)
    print("Limpiando datos de prueba anteriores...")
    c.execute("DELETE FROM rendicion_items")
    c.execute("DELETE FROM rendiciones")
    c.execute("DELETE FROM robos_mermas")
    c.execute("DELETE FROM workers WHERE is_admin = 0")
    conn.commit()

    c.execute("SELECT id, name FROM modulos")
    modulos = c.fetchall()

    if not modulos:
        print("Error: No hay módulos creados.")
        return

    # 2. RECLUTAMIENTO FORZADO PARA TODOS LOS MÓDULOS
    print(f"Reclutando personal para {len(modulos)} módulos...")
    default_pass = generate_password_hash("123456")
    workers_data = []

    for mod_id, mod_name in modulos:
        tipos = ["Full Time", "Full Time", "Part Time", "Part Time"]
        for i in range(4):
            # Usamos un RUT fijo basado en la iteración para no inflar la DB si lo corres sin limpiar
            rut_falso = f"{10 + i}.{mod_id:03d}.100-{i}"
            nombre_falso = f"Trabajador {i+1} ({mod_name})"
            phone_falso = f"+56 9 8888 {mod_id:02d}{i:02d}"

            banco = random.choice(["Banco Estado", "Banco de Chile", "Banco Falabella", "Santander", "BCI", "Scotiabank"])
            workers_data.append((
                rut_falso, nombre_falso, phone_falso,
                default_pass, 0, mod_id, tipos[i],
                banco, f"{random.randint(10000000, 99999999)}", random.choice(["Cuenta Corriente", "Cuenta Vista", "Cuenta Rut"]),
                f"{random.randint(10000000, 99999999)}-{random.choice('0123456789K')}",
            ))

    c.executemany('''INSERT OR IGNORE INTO workers 
                     (rut, name, phone, password_hash, is_admin, modulo_id, tipo,
                      nombre_banco, numero_cuenta, tipo_cuenta, rut_banco)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', workers_data)
    conn.commit()

    # 2.5 GENERACIÓN DE HISTORIAL DE PRECIOS MOCK
    print("Generando fluctuaciones de precios históricas de prueba...")
    c.execute("SELECT id FROM productos")
    prod_ids = [row[0] for row in c.fetchall()]
    c.execute("SELECT id FROM zonas")
    zona_ids = [row[0] for row in c.fetchall()]

    precios_historicos_extra = []
    hoy = date.today()
    
    for p_id in prod_ids:
        for z_id in zona_ids:
            c.execute("SELECT price, commission FROM precios_historicos WHERE producto_id = ? AND zona_id = ? ORDER BY fecha_activacion ASC LIMIT 1", (p_id, z_id))
            base_row = c.fetchone()
            if not base_row:
                continue
            base_price, base_comm = base_row
            
            # Create 3 historical price changes in the last 180 days
            intervalos = [140, 80, 30]
            current_price = base_price
            current_comm = base_comm
            for dias in intervalos:
                if random.random() < 0.70:
                    change_percent = random.choice([-0.15, -0.10, 0.05, 0.10, 0.15, 0.20])
                    current_price = int(current_price * (1 + change_percent))
                    current_price = max(1000, (current_price // 100) * 100)
                    
                    comm_change = random.choice([-50, 0, 50, 100])
                    current_comm = max(100, current_comm + comm_change)
                    
                    fecha_cambio = (hoy - timedelta(days=dias)).strftime('%Y-%m-%d 00:00:00')
                    precios_historicos_extra.append((p_id, z_id, current_price, current_comm, fecha_cambio))

    c.executemany('''INSERT INTO precios_historicos 
                     (producto_id, zona_id, price, commission, fecha_activacion)
                     VALUES (?, ?, ?, ?, ?)''', precios_historicos_extra)
    conn.commit()

    # 2.6 CREACIÓN DE COMPLEMENTOS Y VÍNCULOS CON PRODUCTOS
    print("Creando complementos y vinculándolos con productos...")
    
    # Lista de complementos según la planilla
    complementos_nuevos = [
        "LENTE SOL", "POLARIZADO", "ANTIPARRA GRAN", "ANTIPARRA MED", 
        "ANTIPARRA PEQ", "FILTRO AZUL", "JOCKEY 2X", "ESTUCHE MODA",
        "ESTUCHE CIERRE", "ESTUCHE LECTUR", "STRAP TELA", "STRAP DISEÑO",
        "STRAP CUERO", "MP FUNDAS", "PIROS TALE", "BOLSA", "ETIQUETA"
    ]
    
    # Crear complementos si no existen
    complementos_map = {}  # name -> id
    c.execute("SELECT id, name FROM complementos")
    for row in c.fetchall():
        complementos_map[row[1]] = row[0]
    
    for comp_name in complementos_nuevos:
        if comp_name not in complementos_map:
            c.execute("INSERT INTO complementos (name) VALUES (?)", (comp_name,))
            complementos_map[comp_name] = c.lastrowid
    
    # Mapeo de productos a complementos según la planilla
    # Formato: nombre_producto -> [(nombre_complemento, cantidad), ...]
    producto_complementos_map = {
        "PACK LENTES DE SOL 1 x": [("MP FUNDAS", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "PACK LENTES DE PANTALLA": [("MP FUNDAS", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "PACK LENTES DE SOL 2 x": [("MP FUNDAS", 2), ("BOLSA", 1), ("ETIQUETA", 1)],
        "PACK LENTES DE SOL 3 x": [("MP FUNDAS", 3), ("BOLSA", 1), ("ETIQUETA", 1)],
        "PACK LENTES + ESTUCHE BLANDO": [("ESTUCHE MODA", 1), ("MP FUNDAS", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "PACK LENTES + STRAP": [("STRAP DISEÑO", 1), ("STRAP CUERO", 1), ("MP FUNDAS", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "PACK LENTES 1 x POLARIZADO + ESTUCHE BLANDO+ KIT": [("POLARIZADO", 1), ("ESTUCHE MODA", 1), ("MP FUNDAS", 1), ("PIROS TALE", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "PACK LENTES 2 x POLARIZADO + 2 ESTUCHE BLANDO+ KIT": [("POLARIZADO", 2), ("ESTUCHE MODA", 2), ("MP FUNDAS", 2), ("PIROS TALE", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "PACK LENTES GRANDES ANTIPARRA CON LIGA": [("ANTIPARRA GRAN", 1), ("MP FUNDAS", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "ANTIPARRA MEDIANO": [("MP FUNDAS", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "ANTIPARRA PEQUEÑO": [("MP FUNDAS", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "PACK LENTES DE GRADUACION": [("FILTRO AZUL", 1), ("ESTUCHE LECTUR", 1), ("PIROS TALE", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "PACK LENTES FILTRO AZUL": [("JOCKEY 2X", 1), ("ESTUCHE MODA", 1), ("PIROS TALE", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "JOCKEY (2 X PROD. SELECCIONADO)": [("JOCKEY 2X", 2), ("BOLSA", 1), ("ETIQUETA", 1)],
        "ESTUCHES MODA": [("ESTUCHE MODA", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "ESTUCHES CIERRE": [("ESTUCHE CIERRE", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "ESTUCHE DE LECTURA": [("ESTUCHE LECTUR", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "STRAP TELA": [("STRAP TELA", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "STRAP DISEÑO": [("STRAP DISEÑO", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "STRAP CUERO": [("STRAP CUERO", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "LIMPIA CRISTAL + PAÑO": [("MP FUNDAS", 1), ("PIROS TALE", 1), ("BOLSA", 1), ("ETIQUETA", 1)],
        "LENTE LED": [("BOLSA", 1), ("ETIQUETA", 1)],
        "PULSERAS": [("BOLSA", 1), ("ETIQUETA", 1)],
        "SUJETADORES PARA LENTES": [("BOLSA", 1), ("ETIQUETA", 1)],
        "CORREAS DE CARTERAS DELGADAS Y GRUESAS": [("BOLSA", 1), ("ETIQUETA", 1)],
        "ESTUCHE COLGANTE DE LENTES": [("BOLSA", 1), ("ETIQUETA", 1)],
        "COLGANTE DE CELULAR (PULSERA)": [("BOLSA", 1), ("ETIQUETA", 1)],
        "COLGANTE DE CELULAR (COLLAR)": [("BOLSA", 1), ("ETIQUETA", 1)],
        "PACK DUO DE COLGANTE DE CELULAR": [("BOLSA", 1), ("ETIQUETA", 1)],
        "JOCKEY, GORRAS, SOMBREROS, CUELLOS Y OTROS.": [("BOLSA", 1), ("ETIQUETA", 1)],
        "CARTERAS ORDENADOR": [("BOLSA", 1), ("ETIQUETA", 1)],
    }
    
    # Obtener IDs de productos
    c.execute("SELECT id, name FROM productos")
    productos_db = {row[1]: row[0] for row in c.fetchall()}
    
    # Insertar relaciones producto-complemento
    vinculos_creados = 0
    for prod_name, complementos_list in producto_complementos_map.items():
        if prod_name in productos_db:
            prod_id = productos_db[prod_name]
            for comp_name, cantidad in complementos_list:
                if comp_name in complementos_map:
                    comp_id = complementos_map[comp_name]
                    # Verificar si ya existe la relación
                    c.execute("SELECT id FROM producto_complementos WHERE producto_id = ? AND complemento_id = ?", (prod_id, comp_id))
                    if not c.fetchone():
                        c.execute("INSERT INTO producto_complementos (producto_id, complemento_id, cantidad) VALUES (?, ?, ?)", (prod_id, comp_id, cantidad))
                        vinculos_creados += 1
    
    conn.commit()
    print(f"  - {len(complementos_nuevos)} complementos creados/verificados")
    print(f"  - {vinculos_creados} vínculos producto-complemento creados")

    # 3. PREPARACIÓN DE DATOS
    c.execute("SELECT id, modulo_id, tipo FROM workers WHERE is_admin = 0")
    all_workers_data = c.fetchall()
    todos_los_trabajadores = [w[0] for w in all_workers_data]
    workers_tipo = {w[0]: w[2] for w in all_workers_data}

    trabajadores_por_modulo = {}
    for w_id, m_id, _ in all_workers_data:
        if m_id not in trabajadores_por_modulo:
            trabajadores_por_modulo[m_id] = []
        trabajadores_por_modulo[m_id].append(w_id)

    c.execute("""
        SELECT p.id, ph.price, ph.commission
        FROM productos p
        JOIN precios_historicos ph ON p.id = ph.producto_id
        GROUP BY p.id
    """)
    productos = c.fetchall()

    # 4. VIAJE EN EL TIEMPO
    hoy = date.today()
    fecha_inicio = hoy - timedelta(days=dias_atras)
    rendiciones_creadas = 0
    
    # Textos de ejemplo para los gastos
    motivos_gastos = [
        "Compra bidón de agua", 
        "Artículos de aseo", 
        "Lápices y cuaderno", 
        "Reparación menor del módulo", 
        "Bolsas para entregar productos", 
        "Cinta adhesiva", 
        "Pilas para escáner"
    ]

    print(f"Generando turnos con gastos aleatorios desde {fecha_inicio} hasta {hoy}...")

    for i in range(dias_atras + 1):
        fecha_actual = fecha_inicio + timedelta(days=i)
        fecha_str = fecha_actual.strftime('%Y-%m-%d')
        
        for modulo_id, mod_name in modulos:
            workers_modulo = trabajadores_por_modulo.get(modulo_id, [])
            if not workers_modulo:
                continue
                
            worker_id = random.choice(workers_modulo)

            es_manana = random.choice([True, False])
            if es_manana:
                hora_entrada = f"{random.randint(8, 10):02d}:{random.choice(['00', '30'])}"
                hora_salida = f"{random.randint(14, 16):02d}:{random.choice(['00', '30'])}"
            else:
                hora_entrada = f"{random.randint(13, 15):02d}:{random.choice(['00', '30'])}"
                hora_salida = f"{random.randint(19, 21):02d}:{random.choice(['00', '30'])}"

            worker_tipo = workers_tipo.get(worker_id, "Part Time")
            worker_comision = 1 if worker_tipo == "Full Time" else random.choice([0, 1])

            # Acompañante (70%)
            companion_id = None
            comp_in, comp_out = None, None
            companion_comision = 0
            companion2_id = None
            companion2_comision = 0
            if random.random() < 0.70:
                posibles_comp = [w for w in workers_modulo if w != worker_id]
                if posibles_comp:
                    companion_id = random.choice(posibles_comp)
                    comp_in, comp_out = hora_entrada, hora_salida
                    comp_tipo = workers_tipo.get(companion_id, "Part Time")
                    companion_comision = 1 if comp_tipo == "Full Time" else random.choice([0, 1])

                    # Acompañante 2 (25% probability if companion 1 is present)
                    if random.random() < 0.25:
                        posibles_comp2 = [w for w in posibles_comp if w != companion_id]
                        if posibles_comp2:
                            companion2_id = random.choice(posibles_comp2)
                            comp2_tipo = workers_tipo.get(companion2_id, "Part Time")
                            companion2_comision = 1 if comp2_tipo == "Full Time" else random.choice([0, 1])

            # If there is no companion, comision should be disabled (0)
            if companion_id is None:
                companion_comision = 0
            if companion2_id is None:
                companion2_comision = 0

            num_prods = random.randint(1, 5)
            prods_elegidos = random.sample(productos, min(num_prods, len(productos)))
            items_a_insertar = []
            total_calculado = 0

            for prod in prods_elegidos:
                p_id, p_price, p_comm = prod
                cantidad = random.randint(1, 6)
                items_a_insertar.append((p_id, cantidad, p_price, p_comm))
                total_calculado += (p_price * cantidad)

            debito, credito, mp, efectivo = 0, 0, 0, 0
            b_debito, b_credito, b_mp, b_efectivo = 0, 0, 0, 0

            divisiones = random.randint(1, 3)
            monto_restante = int(total_calculado)
            metodos = ["debito", "credito", "mp", "efectivo"]
            random.shuffle(metodos)

            for idx, metodo in enumerate(metodos[:divisiones]):
                monto = monto_restante if idx == divisiones - 1 else random.randint(0, monto_restante // 2)
                monto_restante -= monto

                if monto > 0:
                    boletas = max(1, min(4, monto // 15000))
                    if metodo == "debito": debito, b_debito = monto, boletas
                    elif metodo == "credito": credito, b_credito = monto, boletas
                    elif metodo == "mp": mp, b_mp = monto, boletas
                    elif metodo == "efectivo": efectivo, b_efectivo = monto, boletas

            tipo_registro = "Turno histórico"

            # 15% de probabilidad de tener un gasto en el turno (entre $2.000 y $15.000)
            gastos = 0
            if random.random() < 0.15:
                gastos = random.randint(2, 15) * 1000
                tipo_registro += f" | {random.choice(motivos_gastos)}"

            c.execute('''
                INSERT INTO rendiciones 
                (worker_id, worker_comision, companion_id, companion2_id, modulo_id, fecha,
                 hora_entrada, hora_salida, companion_hora_entrada, companion_hora_salida,
                 companion_comision, companion2_comision,
                 venta_debito, venta_credito, venta_mp, venta_efectivo,
                 boletas_debito, boletas_credito, boletas_mp, boletas_efectivo,
                 gastos, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (worker_id, worker_comision, companion_id, companion2_id, modulo_id, fecha_str,
                  hora_entrada, hora_salida, comp_in, comp_out,
                  companion_comision, companion2_comision,
                  debito, credito, mp, efectivo,
                  b_debito, b_credito, b_mp, b_efectivo,
                  gastos, tipo_registro))

            r_id = c.lastrowid

            for item in items_a_insertar:
                p_id, cant, p_price, p_comm = item
                c.execute('''
                    INSERT INTO rendicion_items (rendicion_id, producto_id, cantidad, precio_historico, comision_historica)
                    VALUES (?, ?, ?, ?, ?)
                ''', (r_id, p_id, cant, p_price, p_comm))

            rendiciones_creadas += 1

    conn.commit()
    print(f"Éxito: Se inyectaron {rendiciones_creadas} rendiciones para TODOS los módulos.")

    # 5. GENERACIÓN DE ROBOS Y MERMAS
    print("Generando reportes de robos y mermas...")
    
    motivos_observaciones = [
        "Producto encontrado dañado en estante",
        "Cliente reportó producto faltante",
        "Inventario no cuadra al cierre de turno",
        "Producto extraviado durante transporte",
        "Daño por manipulación incorrecta",
        "Producto vencido o en mal estado",
        "Pérdida no explicada en conteo",
        ""  # Sin observaciones
    ]
    
    robos_creados = 0
    mermas_creados = 0
    
    for i in range(dias_atras + 1):
        fecha_actual = fecha_inicio + timedelta(days=i)
        fecha_str = fecha_actual.strftime('%Y-%m-%d')
        
        for modulo_id, mod_name in modulos:
            workers_modulo = trabajadores_por_modulo.get(modulo_id, [])
            if not workers_modulo:
                continue
            
            # 8% de probabilidad de tener un reporte de robo/merma por día por módulo
            if random.random() < 0.08:
                worker_id = random.choice(workers_modulo)
                
                # Elegir 1-4 productos aleatorios
                num_productos = random.randint(1, 4)
                productos_afectados = random.sample(productos, min(num_productos, len(productos)))
                
                for prod in productos_afectados:
                    p_id, p_price, p_comm = prod
                    cantidad = random.randint(1, 5)
                    
                    # 40% robo, 60% merma
                    motivo = "robo" if random.random() < 0.40 else "merma"
                    
                    # Observaciones (70% de probabilidad de tener observación)
                    observaciones = random.choice(motivos_observaciones) if random.random() < 0.70 else ""
                    
                    c.execute('''
                        INSERT INTO robos_mermas 
                        (worker_id, modulo_id, fecha, producto_id, cantidad, motivo, observaciones)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (worker_id, modulo_id, fecha_str, p_id, cantidad, motivo, observaciones))
                    
                    if motivo == "robo":
                        robos_creados += 1
                    else:
                        mermas_creados += 1
    
    conn.commit()
    print(f"  - {robos_creados} registros de robos creados")
    print(f"  - {mermas_creados} registros de mermas creados")

    conn.close()
    print(f"\n=== RESUMEN FINAL ===")
    print(f"Rendiciones: {rendiciones_creadas}")
    print(f"Robos: {robos_creados}")
    print(f"Mermas: {mermas_creados}")
    print(f"Total registros generados: {rendiciones_creadas + robos_creados + mermas_creados}")

if __name__ == '__main__':
    generar_historico_definitivo()