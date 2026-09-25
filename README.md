# SmartWallet: entorno didáctico de analítica de datos en Fintech

Materiales del Trabajo Fin de Máster *"Desarrollo de un entorno didáctico de sistemas de soporte a la decisión y analítica de datos en Fintech: caso de optimización de campañas de promoción de stablecoins"*.

**Autora:** Lucía Liaño González  
**Directora:** María Paula De Toledo  
**Máster Universitario en FINTECH: Tecnologías para el sector financiero**, Universidad Carlos III de Madrid, curso 2025-2026.

## El caso

Una entidad financiera quiere promocionar entre sus clientes una Smart Wallet basada en stablecoins y dispone de dos tipos de cupón promocional: uno gratuito pero limitado (3.000 unidades, 1 % de comisión) y otro con coste por cliente (2,85 €, 2,5 % de comisión). El alumnado debe decidir a qué clientes ofrecer cada cupón para maximizar el beneficio de la campaña, a partir de una población sintética de 300.000 clientes calibrada con datos del INE y la AEAT.

## Contenido del repositorio

| Carpeta | Contenido |
|---|---|
| `Documentos/` | Enunciados y guías de las prácticas: guía de la Práctica 1 (Tableau), su solución para el profesorado y el enunciado del caso final (Práctica 2). |
| `python/` | Generación de los datos, preparación del conjunto unificado, soluciones de referencia, criterios de reparto y script de corrección de las entregas. |
| `R/` | Selección de hiperparámetros (número de clústeres y de árboles) e implementación completa del modelado en R. |
| `rapidminer/` | Procesos de RapidMiner (`.rmp`) de minería de texto y de modelado. |
| `datos/` | Ficheros de entrada del generador (INE y AEAT) y corpus de comentarios `COMENTARIOS_STABLECOINS.txt`. |

### Scripts

| Script | Función |
|---|---|
| `python/generar_datos_tfm.py` | Genera `clientes.txt`, `transacciones.txt` y `stablecoins.txt`, además del fichero oculto de validación. |
| `python/juntarTablas.py` | Agrega las transacciones por cliente y construye `union_dataset.csv`. |
| `R/n_clusters.R` | Evalúa el número de clústeres con WCSS, Davies-Bouldin y silueta. |
| `R/n_arboles.R` | Evalúa el número de árboles del Random Forest con el error OOB. |
| `R/Proceso_completo.R` | Réplica en R del proceso de RapidMiner (K-Means y Random Forest). |
| `python/correlacion_R_RapidMiner.py` | Compara las salidas de scoring de RapidMiner y R. |
| `python/benchmarks_referencia.py` | Calcula las soluciones de referencia sin modelo predictivo. |
| `python/explorar_criterios.py` | Aplica los criterios de reparto de cupones A, B, C y D. |
| `python/valorar_alumnos.py` | Calcula el beneficio de cada propuesta y genera el informe de cada grupo. |

## Cómo reproducir el caso

Los ficheros de datos no se incluyen por su tamaño; se generan con el propio código.

1. **Generar los datos:** ejecutar `python/generar_datos_tfm.py`. Necesita `poblacionPorEdad.xlsx` y `RentaPorDP.xlsx` (carpeta `datos/`). La semilla está fijada, por lo que el resultado es reproducible.
2. **Construir el conjunto unificado:** ejecutar `python/juntarTablas.py`.
3. **Modelado:** ejecutar los scripts de `R/` o abrir los procesos de `rapidminer/`.
4. **Reparto y evaluación:** ejecutar `python/explorar_criterios.py` y `python/valorar_alumnos.py`.

> **Importante:** las rutas de lectura y escritura de los scripts corresponden al equipo en el que se desarrolló el trabajo (`D:\Master\TFM\...`) y deben adaptarse antes de ejecutarlos.

### Requisitos

- **Python 3**, con `pandas`, `numpy` y `openpyxl`.
- **R**, con `randomForest`, `cluster`, `clusterSim`, `dplyr`, `fastDummies` y `factoextra`.
- **RapidMiner Studio / Altair AI Studio** y **Tableau** para las partes visuales.
