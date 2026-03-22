# KSNE-Rendiciones-App

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
# TODO preguntas:
- ver si tienen como turnos fijos para setear un horario
- ver si trabajan mas de 2 personas maximo al dia
- ver como funcionan los productos / precios de HC

# TODO general:
- generar reportes y exportar a excel
- tabla de productos vendidos durante el mes
- formulario de cosas robadas
- implementar horas extra?
- implemetar calendario como el excel
- arrglar colores en modo claro y oscuro
- separar productos para tiendas
- limpiar requirements.txt
- mostrar rendiciones antiguas
- mostrar total de ventas con graficos en el index(?)
- mostrar ventas diarias por modulo y zona(?)
- formulario de perdidas en el dashboard(?) o hub
- categorias de productos (complementos, etc)
- precio de productos por zona
- proteccion contra borrado de zonas o modulos si ya estan asignados a algo
- hacer que contraseña autogenerada force a crear una nueva para el trabajador

# TODO no prioritario:
- dejar mas bonito las cosas de admin en media ventana o otros formatos

# TODO peppermint:
## formulario
- cantidad de boletas por metodo de pago
- permitir subir foto de total gastos (boleta/factura)

# TODO happy candy:
- comision 2%