# App TPA Aragón · Concesión T05

Aplicación web móvil dedicada exclusivamente a la concesión T05 y a las líneas T05-01, T05-20 y T05-50.

## Pantallas

- **Inicio:** cabecera TPA / Gobierno de Aragón, franja de transporte, mapa de paradas y navegación inferior.
- **Líneas:** buscador y listado únicamente de T05-01, T05-20 y T05-50.
- **Ida / Vuelta:** cada línea muestra los dos sentidos disponibles en el GTFS.
- **Recorrido:** mapa del sentido seleccionado y lista vertical de paradas ordenadas.
- **Parada:** ficha inferior compacta con minimapa de ubicación, nombre, selector de las líneas que paran allí, pestañas Hoy/Mañana y llegadas programadas/predicciones en tiempo real cuando el feed las proporciona.

La misma pantalla de parada se abre desde los marcadores del mapa, el mapa del recorrido y la lista de paradas. Se reutiliza el motor de horarios y tiempo real de la aplicación original; la interfaz móvil no crea datos de llegada ficticios.

## Despliegue en Render

El ZIP original se conserva como `mapa-tpa-main (1).zip`. En cada build, `render_setup.py` extrae ese proyecto, incorpora el endpoint de recorridos T05 con fallback al catálogo de paradas y lectura de direction_id de GTFS, copia `t05-mobile.js` a los estáticos Flask e inserta su referencia en la plantilla original.

1. En Render, selecciona **New + → Blueprint**.
2. Conecta `lhuisherandez-create/app-tpa`.
3. Render detectará `render.yaml`. Pulsa **Apply**.
4. Los nuevos commits en `main` activan el despliegue automático.

## Comprobaciones automáticas

GitHub Actions ejecuta el mismo build que Render, comprueba la sintaxis de `t05-mobile.js` con Node y compila la aplicación Python.

## Ejecución local

```bash
python render_setup.py
pip install -r mapa-tpa-main/requirements.txt
cd mapa-tpa-main
gunicorn app:app
```
