# KSNE

Key Sales & Net Earnings — Sistema de rendiciones, inventario y reportes para módulos retail.

## Arquitectura

### Stack
- Flask 3.1 + SQLAlchemy 2.0
- SQLite (persiste en volumen Docker)
- Bootstrap 5.3 (dark mode, responsive)
- openpyxl (exportación Excel)

### Módulos
- **Auth**: login/logout con RUT + contraseña
- **Worker**: dashboard, rendiciones, reporte de robos y mermas
- **Admin**: CRUD de workers, productos/precios, reportes con exportación Excel

### Reportes disponibles

| Reporte | Ruta | Excel |
|---|---|---|
| Detalle de Ventas | `/reportes/modulo/<id>` | ✅ |
| Centros Comerciales | `/reportes/modulo/<id>/centros_comerciales` | ✅ |
| Control % Ventas Efectivo/Tarjetas | `/reportes/modulo/<id>/calculo_iva` | ✅ |
| Robos y Mermas | `/reportes/modulo/<id>/robos_mermas` | ✅ |
| Productos Vendidos y Complementos | `/reportes/modulo/<id>/productos_vendidos` | ✅ |
| Comisiones | `/reportes/modulo/<id>/comisiones` | — |
| Horarios | `/reportes/modulo/<id>/horarios` | — |

### Complementos
Cada producto puede tener complementos vinculados (ej. "Paño" con "ANTIPARRA MEDIANO").
Al vender un producto, sus complementos se registran como egresos de inventario.

## Docker Deployment

### Requisitos
- Docker + Docker Compose
- Volúmenes persistentes en `/home/sekidesu/dockerVolumes/ksne/`

### Deploy

```bash
./build-deploy.sh    # git pull + build + up

# O paso a paso:
docker compose up -d --build
```

La app estará disponible en `http://localhost:5500`.

### Reiniciar datos de prueba

```bash
docker exec -it ksne-server python generar_unificado.py
```

### Volúmenes

Los datos persistentes se almacenan fuera del contenedor:

| Ruta host | Ruta container | Propósito |
|---|---|---|
| `/home/sekidesu/dockerVolumes/ksne/db` | `/app/db` | Base de datos SQLite |
| `/home/sekidesu/dockerVolumes/ksne/static/cache` | `/app/static/cache` | Archivos cacheados |

## Credenciales por defecto

| Rol | RUT | Contraseña |
|---|---|---|
| Admin | `1-9` | `admin123` |
| Worker | `11.111.111-1` | `123456` |

# TODO

## General
- [ ] Separar productos por tienda
- [ ] Mostrar gráficos de ventas totales en el index
- [ ] Mostrar ventas diarias por módulo/zona
- [ ] Fix colors in light/dark mode
- [ ] Force password change on first login for workers
- [ ] Clean up requirements.txt

## Low Priority
- [ ] Polish admin UI layout

## Peppermint
- [ ] Receipt count by payment method
- [ ] Allow uploading expense receipt photos

## Happy Candy
- [ ] 2% commission
