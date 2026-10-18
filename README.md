# Análisis de teoría de colas – Audifarma, sede Plaza del Sol (Soledad)

Código del trabajo de grado *Diagnóstico del proceso de atención y comparación de los
modelos de teoría de colas M/M/1, M/M/s y M/G/1 en Audifarma S.A. sede Plaza del Sol
de Soledad* (Ingeniería Industrial, Universidad Libre Seccional Barranquilla, 2026).

Autores: Joshua Alain Gutiérrez Arenas y Cesar Luis López Ortiz.

## Datos
`Datos_Audifarma.xlsx`: registro de 420 atenciones, llegadas por día y franja (10 días),
intervalos de 5 minutos y tiempos entre llegadas. `tiempos_servicio.csv`: los 420 tiempos
de servicio en minutos.

## Requisitos
pip install numpy scipy simpy matplotlib openpyxl

## Scripts
| Script | Genera |
|---|---|
| figura3.py, figura4.py | Figuras 3 y 4 |
| simulacion_audifarma.py | Figuras 5, 11 y 12; Tabla 16 |
| prueba_llegadas.py | Figura 6; Tabla 7 |
| prueba_servicio.py | Figura 7; Tabla 8 |
| modelos_colas.py | Tablas 9, 10 y 11 |
| validacion_modelos.py | Figuras 8 y 9; Tabla 12 |
| dimensionamiento.py | Tablas 14 y 15; Figura 10 |
| analisis_complementario.py | Validación, sensibilidad y costo diario |

Uso: `python nombre_del_script.py` desde esta carpeta. Todos usan semilla fija,
así que los resultados son reproducibles.
