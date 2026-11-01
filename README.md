# App TPA Aragón

Aplicación web Flask para consultar líneas, rutas y paradas de transporte público de Aragón, con una interfaz móvil inspirada en las capturas facilitadas.

## Despliegue en Render

El proyecto original está guardado en el repositorio como `mapa-tpa-main (1).zip`. El script `render_setup.py` lo extrae durante la fase de build y aplica los ajustes de interfaz móvil antes de instalar las dependencias.

1. Entra en [Render](https://render.com/).
2. Selecciona **New + → Blueprint**.
3. Conecta el repositorio `lhuisherandez-create/app-tpa`.
4. Render detectará `render.yaml`. Pulsa **Apply** para crear el servicio `app-tpa`.

La configuración realiza automáticamente:

- Extracción del proyecto original en `mapa-tpa-main/`.
- Aplicación de la cabecera Jiménez / Gobierno de Aragón, navegación inferior y buscador de líneas.
- Instalación de `mapa-tpa-main/requirements.txt`.
- Arranque con Gunicorn en el puerto asignado por Render.
- Despliegue automático cuando se actualice la rama principal.

## Ejecución local

```bash
python render_setup.py
pip install -r mapa-tpa-main/requirements.txt
cd mapa-tpa-main
gunicorn app:app
```
