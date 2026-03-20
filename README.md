# Rendiciones-App

## 🐳 Docker Deployment (Server)

Build and run the central inventory server:

```bash
# Build the image
docker build -t rendiciones:latest .

# Run the container (Map port 5000 and persist the database/cache)
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/rendiciones/db:/app/db \
  -v $(pwd)/rendiciones/static/cache:/app/static/cache \
  --name rendiciones-server \
  --restart unless-stopped \
  rendiciones:latest
```

Or use this stack:
```yml
name: rendiciones
services:
    rendiciones:
        ports:
            - 5000:5000
        volumes:
            - YOUR_PATH/rendiciones/db:/app/db
            - YOUR_PATH/rendiciones/static/cache:/app/static/cache
        container_name: rendiciones-server
        image: rendiciones:latest
        restart: unless-stopped
```

# TODO general:
- separar productos para tiendas
- limpiar requirements.txt
- hacer prompts mas bonitos y estandar

# TODO peppermint:
## formulario
- cantidad de boletas por metodod de pago
- añadir segunda persona a cargo
- verificar que todos los campos esten rellenos
- separar credito y debito
- permitir subir foto de total gastos (boleta/factura)
## otros
- bloquear turno para otra persona si ya fue subido por otra persona
- part time hora entrada y salida sin comisiones
- ocaciones especiales permiten comisiones (en panel admin)

# TODO happy candy:
- total vendido
- comision 2%