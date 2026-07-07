# KSNE

Key Sales & Net Earnings — Settlement, inventory and reporting system for retail modules.

## Architecture

### Stack
- Flask 3.1 + Flask-SQLAlchemy 2.0 (with raw sqlite3 for bootstrap/seed)
- SQLite (persists in Docker volume)
- gunicorn (production server)
- Bootstrap 5.3 (dark mode, responsive)
- openpyxl (Excel export)

### Modules
- **Auth**: login/logout with RUT + password
- **Worker**: dashboard with settlement history, new settlement form (with products, companion, schedules), theft & shrinkage report
- **Admin**: CRUD for workers (with bank details), zones/modules, products & per-zone scheduled prices, complementos (add-ons), rendiciones management, and multi-format reports with Excel export

### Available Reports

| Report | Route | Excel |
|---|---|---|
| Sales Detail | `/admin/reportes/modulo/<id>` | ✅ |
| Shopping Centers | `/admin/reportes/modulo/<id>/centros_comerciales` | ✅ |
| Cash/Card Sales % Control | `/admin/reportes/modulo/<id>/calculo_iva` | ✅ |
| Theft and Shrinkage | `/admin/reportes/modulo/<id>/robos_mermas` | ✅ |
| Sold Products and Add-ons | `/admin/reportes/modulo/<id>/productos_vendidos` | ✅ |
| Commissions | `/admin/reportes/modulo/<id>/comisiones` | — |
| Schedules | `/admin/reportes/modulo/<id>/horarios` | — |

### Complementos (Add-ons)
Each product can have linked complementos (e.g. "PACK LENTES DE SOL 1" linked to "MEDIUM GOGGLE"). When a product is sold, its complementos are tracked as inventory outflows. The Sold Products report breaks down quantities by product sales, complementos delivered, and theft/shrinkage.

## Docker Deployment

### Requirements
- Docker + Docker Compose
- Persistent volumes at `/home/sekidesu/dockerVolumes/ksne/`

### Build & Deploy

```bash
docker build -t ksne:latest .
docker compose up -d
```

The app will be available at `http://localhost:5500`.

### Volumes

Persistent data is stored outside the container:

| Host path | Container path | Purpose |
|---|---|---|
| `/home/sekidesu/dockerVolumes/ksne/db` | `/app/db` | SQLite database |
| `/home/sekidesu/dockerVolumes/ksne/static/cache` | `/app/static/cache` | Cached files |

## Default Credentials

| Role | RUT | Password |
|---|---|---|
| Admin | `1-9` | `admin123` |
| Worker | `11.111.111-1` | `123456` |

# TODO

## General
- [ ] Separate products by store
- [ ] Show total sales charts on index
- [ ] Show daily sales by module/zone
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
