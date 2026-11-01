# App TPA Aragón · Concesión T05

Aplicación web móvil para consultar exclusivamente las tres rutas GTFS de la concesión T05: T05-01, T05-20 y T05-50.

## Funcionalidad

- Inicio abre directamente el mapa con las paradas de T05.
- Líneas muestra T05-01, T05-20 y T05-50.
- Cada línea muestra sus paradas en el orden del GTFS oficial.
- Seleccionar una parada desde la lista o el mapa abre la misma ficha inferior.
- La ficha permite consultar Hoy y Mañana, horarios oficiales y favoritos.
- El seguimiento en tiempo real se mantiene para T05 cuando el feed está disponible.

## Despliegue en Render

El proyecto fuente está en `mapa-tpa-main (1).zip`. El script `render_setup.py` realiza una extracción limpia, añade el endpoint de paradas ordenadas por ruta y prepara la interfaz móvil durante el build.

1. Entra en [Render](https://render.com/).
2. Selecciona **New + → Blueprint**.
3. Conecta `lhuisherandez-create/app-tpa`.
4. Render detectará `render.yaml`. Pulsa **Apply** para crear el servicio `app-tpa`.

Render instalará las dependencias y arrancará Flask con Gunicorn en el puerto asignado.

## Ejecución local

```bash
python render_setup.py
pip install -r mapa-tpa-main/requirements.txt
cd mapa-tpa-main
gunicorn app:app
```
