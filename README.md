# App TPA Aragón · Concesión T05

Aplicación web móvil para consultar exclusivamente la concesión T05 y sus líneas T05-01, T05-20 y T05-50.

## Interfaz móvil

- **Inicio:** mapa de las paradas de la concesión T05.
- **Líneas:** listado de T05-01, T05-20 y T05-50.
- Al abrir una línea se muestran los sentidos **Ida** y **Vuelta**.
- Cada sentido presenta el trazado en el mapa y las paradas en orden GTFS.
- Al tocar cualquier parada, tanto en el mapa principal como en el trazado o en el listado, aparece la misma ficha fija.
- La ficha incluye un minimapa de ubicación, selector de líneas que sirven la parada y llegadas programadas/tiempo real cuando hay predicciones disponibles.
- Favoritos y consulta de Hoy/Mañana.

## Despliegue en Render

El proyecto original se conserva en `mapa-tpa-main (1).zip`. El script `render_setup.py` extrae el proyecto en cada build, prepara el endpoint de sentidos GTFS e instala el interfaz móvil `t05-mobile.js` dentro de los estáticos Flask.

1. En Render selecciona **New + → Blueprint**.
2. Conecta `lhuisherandez-create/app-tpa`.
3. Render detectará `render.yaml`. Pulsa **Apply** para crear el servicio.
4. Los nuevos commits en `main` lanzan un despliegue automático.

## Ejecución local

```bash
python render_setup.py
pip install -r mapa-tpa-main/requirements.txt
cd mapa-tpa-main
gunicorn app:app
```
