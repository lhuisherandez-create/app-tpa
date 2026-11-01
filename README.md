# App TPA Aragón

Aplicación web Flask para consultar líneas, rutas y paradas de transporte público de Aragón.

## Despliegue en Render

Este repositorio incluye `render.yaml`. En Render selecciona **New + → Blueprint**, conecta este repositorio y confirma la creación del servicio web `app-tpa`.

- Runtime: Python
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT`

La carga completa del catálogo y los datos GTFS del proyecto original debe incorporarse antes de dar por terminada la migración funcional.
