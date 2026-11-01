# App TPA Aragón · Concesión T05

Aplicación web móvil para consultar exclusivamente la concesión T05 y sus tres líneas: T05-01, T05-20 y T05-50.

## Menús y flujo de uso

- **Inicio:** abre el mapa con las paradas de T05 y los controles del mapa.
- **Líneas:** muestra un buscador y únicamente T05-01, T05-20 y T05-50.
- Al abrir una línea aparecen sus sentidos **Ida** y **Vuelta**.
- Al elegir un sentido se muestra el mapa del recorrido y la lista vertical de paradas en orden GTFS.
- Al pulsar una parada desde el mapa, el recorrido o la lista se abre la misma ficha inferior.
- La ficha presenta, en este orden, un minimapa de ubicación, selector **Hoy/Mañana**, nombre de la parada, selector de las líneas que la sirven y llegadas programadas/predicciones en tiempo real si están disponibles.
- Se mantienen los favoritos.

## Despliegue en Render

El proyecto original se conserva en `mapa-tpa-main (1).zip`. El script `render_setup.py` extrae el proyecto en cada build, prepara la API de recorridos T05 e instala la navegación móvil integrada en la plantilla original en los estáticos Flask.

1. En Render, selecciona **New + → Blueprint**.
2. Conecta `lhuisherandez-create/app-tpa`.
3. Render detectará `render.yaml`. Pulsa **Apply**.
4. Los nuevos commits en `main` activan el despliegue automático.

## Comprobaciones automáticas

GitHub Actions ejecuta el mismo script de build que Render, valida la sintaxis JavaScript, compila Python y ejecuta las pruebas del proyecto.

## Ejecución local

```bash
python render_setup_v2.py
pip install -r mapa-tpa-main/requirements.txt
cd mapa-tpa-main
gunicorn app:app
```
