# App TPA Aragón

Aplicación web Flask para consultar líneas, rutas y paradas de transporte público de Aragón.

## Despliegue en Render

El proyecto original está guardado en el repositorio como `mapa-tpa-main (1).zip`. El Blueprint lo descomprime durante la fase de build e instala las dependencias del proyecto.

1. Entra en [Render](https://render.com/).
2. Selecciona **New + → Blueprint**.
3. Conecta el repositorio `lhuisherandez-create/app-tpa`.
4. Render detectará `render.yaml`. Pulsa **Apply** para crear el servicio `app-tpa`.

La configuración realiza automáticamente:

- Extracción del proyecto original en `mapa-tpa-main/`.
- Instalación de `mapa-tpa-main/requirements.txt`.
- Arranque con Gunicorn en el puerto asignado por Render.
- Despliegue automático cuando se actualice la rama principal.

## Ejecución local

```bash
python -m zipfile -e "mapa-tpa-main (1).zip" .
pip install -r mapa-tpa-main/requirements.txt
cd mapa-tpa-main
gunicorn app:app
```
