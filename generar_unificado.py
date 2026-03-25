import random
from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from database import get_db_connection, init_db

def generar_historico_definitivo(dias_atras=180):
    init_db()
    conn = get_db_connection()
    c = conn.cursor()

    # 1. LIMPIEZA TOTAL (Evita el choque con los datos por defecto de database.py)
    print("Limpiando datos de prueba anteriores...")
    c.execute("DELETE FROM rendicion_items")
    c.execute("DELETE FROM rendiciones")
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

            workers_data.append((
                rut_falso, nombre_falso, phone_falso,
                default_pass, 0, mod_id, tipos[i]
            ))

    c.executemany('''INSERT OR IGNORE INTO workers 
                     (rut, name, phone, password_hash, is_admin, modulo_id, tipo) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)''', workers_data)
    conn.commit()

    # 3. PREPARACIÓN DE DATOS
    c.execute("SELECT id, modulo_id FROM workers WHERE is_admin = 0")
    all_workers_data = c.fetchall()
    todos_los_trabajadores = [w[0] for w in all_workers_data]
    
    trabajadores_por_modulo = {}
    for w_id, m_id in all_workers_data:
        if m_id not in trabajadores_por_modulo:
            trabajadores_por_modulo[m_id] = []
        trabajadores_por_modulo[m_id].append(w_id)

    c.execute("SELECT id, price, commission FROM productos")
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
                
            num_turnos = random.randint(1, 2)
            turnos_a_hacer = [True, False] if num_turnos == 2 else [random.choice([True, False])]
            
            for es_manana in turnos_a_hacer:
                # Reemplazos (15%)
                es_reemplazo = random.random() < 0.15
                if es_reemplazo and len(todos_los_trabajadores) > len(workers_modulo):
                    posibles_reemplazos = [w for w in todos_los_trabajadores if w not in workers_modulo]
                    worker_id = random.choice(posibles_reemplazos)
                else:
                    worker_id = random.choice(workers_modulo)
                
                if es_manana:
                    hora_entrada = f"{random.randint(8, 10):02d}:{random.choice(['00', '30'])}"
                    hora_salida = f"{random.randint(14, 16):02d}:{random.choice(['00', '30'])}"
                else:
                    hora_entrada = f"{random.randint(13, 15):02d}:{random.choice(['00', '30'])}"
                    hora_salida = f"{random.randint(19, 21):02d}:{random.choice(['00', '30'])}"
                
                # Acompañante (70%)
                companion_id = None
                comp_in, comp_out = None, None
                if random.random() < 0.70:
                    posibles_comp = [w for w in todos_los_trabajadores if w != worker_id]
                    if posibles_comp:
                        companion_id = random.choice(posibles_comp)
                        comp_in, comp_out = hora_entrada, hora_salida
                
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
                        boletas = random.randint(1, 4)
                        if metodo == "debito": debito, b_debito = monto, boletas
                        elif metodo == "credito": credito, b_credito = monto, boletas
                        elif metodo == "mp": mp, b_mp = monto, boletas
                        elif metodo == "efectivo": efectivo, b_efectivo = monto, boletas

                tipo_registro = "Reemplazo histórico" if es_reemplazo else "Turno histórico"
                
                # === LÓGICA DE GASTOS RANDOM ===
                # 15% de probabilidad de tener un gasto en el turno (entre $2.000 y $15.000)
                gastos = 0
                if random.random() < 0.15:
                    gastos = random.randint(2, 15) * 1000
                    tipo_registro += f" | {random.choice(motivos_gastos)}"

                c.execute('''
                    INSERT INTO rendiciones 
                    (worker_id, companion_id, modulo_id, fecha, hora_entrada, hora_salida, 
                     companion_hora_entrada, companion_hora_salida, 
                     venta_debito, venta_credito, venta_mp, venta_efectivo,
                     boletas_debito, boletas_credito, boletas_mp, boletas_efectivo,
                     gastos, observaciones, worker_comision, companion_comision)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ''', (worker_id, companion_id, modulo_id, fecha_str, hora_entrada, hora_salida,
                      comp_in, comp_out, debito, credito, mp, efectivo,
                      b_debito, b_credito, b_mp, b_efectivo, 
                      gastos, tipo_registro, 1 if companion_id else 0))
                
                r_id = c.lastrowid
                
                for item in items_a_insertar:
                    p_id, cant, p_price, p_comm = item
                    c.execute('''
                        INSERT INTO rendicion_items (rendicion_id, producto_id, cantidad, precio_historico, comision_historica)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (r_id, p_id, cant, p_price, p_comm))
                    
                rendiciones_creadas += 1

    conn.commit()
    conn.close()
    print(f"Éxito: Se inyectaron {rendiciones_creadas} rendiciones para TODOS los módulos.")

if __name__ == '__main__':
    generar_historico_definitivo(180)