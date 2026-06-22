# KSNE-Rendiciones-App

## Docker Deployment

Build and deploy the application:

```bash
./build-deploy.sh    # pulls latest code, builds image, starts container

# Or step by step:
docker compose up -d --build
```

The app will be available at `http://localhost:5500`.

### Volumes

Persistent data is stored outside the container:

| Host path | Container path | Purpose |
|---|---|---|
| `./db` | `/app/db` | SQLite database |
| `./static/cache` | `/app/static/cache` | Cached files |

# TODO
## Questions
- [ ] Verify if shifts are fixed to set a schedule
- [ ] Verify if max 2 people work per day
- [ ] Understand how HC products/prices work

## General
- [ ] Generate shopping center registry
- [ ] Generate reports and export to Excel
- [ ] Monthly sold products table
- [ ] Stolen items form
- [ ] Implement overtime?
- [ ] Implement calendar like Excel
- [ ] Fix colors in light/dark mode
- [ ] Separate products by store
- [ ] Clean up requirements.txt
- [ ] Show total sales charts on index
- [ ] Show daily sales by module/zone
- [ ] Loss report form on dashboard
- [ ] Product categories (complementos, etc)
- [ ] Product pricing by zone
- [ ] Force password change on first login for workers

## Low Priority
- [ ] Polish admin UI layout

## Peppermint
- [ ] Receipt count by payment method
- [ ] Allow uploading expense receipt photos

## Happy Candy
- [ ] 2% commission