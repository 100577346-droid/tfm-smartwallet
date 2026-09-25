"""
Explorar criterios de seleccion sobre el scoring (RapidMiner / R)

Carga los datos y los dos ficheros de scoring,
calcula el beneficio real de cada criterio (A, B, C, D) y lo imprime
por pantalla

Reutiliza (importando, sin copiar) las piezas de valorar_alumnos.py.
"""

import pandas as pd

from valorar_alumnos import (
    PATH_FICHEROS, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2,
    cargar_datos, calcular_beneficio,
)
from benchmarks_referencia import calcular_cortes, repartir_en_tipo1_tipo2

NUM_CODIGOS_T1 = 3000
N2 = 20000  # numero de cupones tipo 2 a repartir en los criterios C y D (que no usan los umbrales de gasto para decidir cuántos, sino un ranking directo).

# carpetas donde vive cada CSV de scoring (distintas de PATH_FICHEROS)
PATH_RAPIDMINER = r"D:\Master\TFM\rapid minner"
PATH_R = r"D:\Master\TFM\R"

CORTE1A, CORTE1B, CORTE2 = calcular_cortes(COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2)


def mostrar_resultado(nombre, resultado):
    """Imprime un resultado de forma legible, lista para copiar al LaTeX."""
    print(f"\n--- {nombre} ---")
    for clave, valor in resultado.items():
        print(f"  {clave}: {valor}")


def cargar_scoring_rapidminer(path_ficheros):
    rm = pd.read_csv(f"{PATH_RAPIDMINER}\\resultado_scoring_stablecoin.csv", sep=";")
    rm = rm.rename(columns={"idCliente": "id", "prediction(gasto_SC)": "prediction_gasto_SC"})
    return rm


def cargar_scoring_r(path_ficheros):
    r = pd.read_csv(f"{PATH_R}\\resultadosR.csv", sep=";", decimal=",")
    r = r.rename(columns={"idCliente": "id"})
    return r


# ==========================================================
# Criterio A - Directo: prediction(gasto_SC) como gasto, reparto por franjas
# ==========================================================

def criterio_a(scoring, stablecoins_futuro):
    """
    Usa solo el gasto predicho por random forest
    Ordena a todos los clientes por gasto predicho, y decide el cupón de cada uno según en qué franja 
    de gasto caiga (0-114€, 114-190€, >190€). (LOS UMBRALES DE SIEMPRE)
    """
    df_pred = scoring.rename(columns={"prediction_gasto_SC": "gasto_futuro"}).copy()
    df_pred["adoptado_futuro"] = 1  # se asume que todos adoptan (igual que modo2_proporcional_ingresos)

    ids1, ids2 = repartir_en_tipo1_tipo2(
        df_pred, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2,
        NUM_CODIGOS_T1, CORTE1A, CORTE1B, CORTE2,
    )
    return calcular_beneficio(ids1, ids2, stablecoins_futuro, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2)


# ==========================================================
# Criterio B - Filtrar por similitud (percentil 75 de distancia), luego A
# ==========================================================

def criterio_b(scoring, stablecoins_futuro, percentil=0.75):
    """
    Elimina al 25% de los clientes que tienen mayor distancia al centroide de su cluster.
    Con solo los que sobrevivieron al filtro (candidatos_cercanos), se reparte cupón 1 o 
    cupón 2 según en qué franja caiga su gasto_futuro (que es la predicción renombrada) 
    respecto a CORTE1A (0€), CORTE1B (114€) y CORTE2 (190€) — los mismos umbrales de siempre.
    """
    limite_distancia = scoring["distancia_centroide"].quantile(percentil) #calcula el valor de distancia_centroide por debajo del cual está el 75% de los clientes
    candidatos_cercanos = scoring[scoring["distancia_centroide"] <= limite_distancia] #Elimina a los usuarios que tienen el 25% más alejados a su centroide

    df_pred = candidatos_cercanos.rename(columns={"prediction_gasto_SC": "gasto_futuro"}).copy()
    df_pred["adoptado_futuro"] = 1

    ids1, ids2 = repartir_en_tipo1_tipo2(
        df_pred, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2,
        NUM_CODIGOS_T1, CORTE1A, CORTE1B, CORTE2,
    )
    return calcular_beneficio(ids1, ids2, stablecoins_futuro, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2)


# ==========================================================
# Criterio C - Puntuacion combinada: prediction_gasto_SC / distancia_centroide
# ==========================================================

def criterio_c(scoring, stablecoins_futuro):
    """
    Crea una columna nueva, score, dividiendo el gasto predicho entre la distancia. 
    Con el fin de combinar las dos señales en un único número, y repartir cupones según ese ranking, ya que cuanto mayor el gasto y
    menor la distancia, mayor el score.
    Ordena por score de mayor a menor. Los primeros N2 van a cupón 2; los siguientes NUM_CODIGOS_T1 (3.000) van a cupón 1. 
    Aquí no se usan los umbrales de gasto (CORTE1A/1B/2) — es un reparto directo por posición en el ranking, no por franjas de gasto.
    """
    puntuado = scoring.copy()
    puntuado["score"] = puntuado["prediction_gasto_SC"] / puntuado["distancia_centroide"]
    ordenado = puntuado.sort_values("score", ascending=False)

    ids2 = ordenado["id"].iloc[:N2]
    ids1 = ordenado["id"].iloc[N2:N2 + NUM_CODIGOS_T1]

    return calcular_beneficio(ids1, ids2, stablecoins_futuro, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2)


# ==========================================================
# Criterio D - Por cluster: priorizar los clusters de mayor gasto medio
# ==========================================================

def criterio_d(scoring, stablecoins_futuro):
    """
    Se agrupan los clientes por cluster, se calcula el gasto medio de cada clúster (usando prediction(gasto_SC)), 
    se ordenan los 8 clústeres de mejor a peor, y se reparte cupón empezando por los clientes del mejor clúster 
    (dentro de cada clúster, ordenados por menor distancia), avanzando al siguiente clúster cuando se agote el cupo. 
    """
    # gasto medio de cada cluster, para ordenar los clusters de mejor a peor
    gasto_medio_cluster = scoring.groupby("cluster")["prediction_gasto_SC"].mean()
    clusters_ordenados = gasto_medio_cluster.sort_values(ascending=False).index.tolist()

    # Recorre los clústeres en ese orden (del mejor al peor) y dentro de cada cluster, ordenamos por menor distancia 
    bloques = []
    for cl in clusters_ordenados:
        #se queda con los clientes de ese clúster, ordenados por menor distancia primero
        bloque = scoring[scoring["cluster"] == cl].sort_values("distancia_centroide", ascending=True)
        bloques.append(bloque) #Los va guardando en la lista bloques
    orden_final = pd.concat(bloques) #los junta todos, uno detrás de otro — así queda una única tabla ordenada: 
    #primero todos los clientes del mejor clúster (por distancia), luego todos los del segundo mejor, y 
    #así sucesivamente.

    ids2 = orden_final["id"].iloc[:N2]
    ids1 = orden_final["id"].iloc[N2:N2 + NUM_CODIGOS_T1]

    return calcular_beneficio(ids1, ids2, stablecoins_futuro, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2)


# ==========================================================
# Programa principal
# ==========================================================

def main():
    stablecoins, stablecoins_futuro = cargar_datos()

    rm = cargar_scoring_rapidminer(PATH_FICHEROS)
    r = cargar_scoring_r(PATH_FICHEROS)

    for nombre_herramienta, scoring in [("RapidMiner", rm), ("R", r)]:
        print(f"\n{'='*60}")
        print(f"  {nombre_herramienta}")
        print(f"{'='*60}")

        mostrar_resultado(f"Criterio A ({nombre_herramienta})", criterio_a(scoring, stablecoins_futuro))
        mostrar_resultado(f"Criterio B ({nombre_herramienta})", criterio_b(scoring, stablecoins_futuro))
        mostrar_resultado(f"Criterio C ({nombre_herramienta})", criterio_c(scoring, stablecoins_futuro))
        mostrar_resultado(f"Criterio D ({nombre_herramienta})", criterio_d(scoring, stablecoins_futuro))


if __name__ == "__main__":
    import sys
    # Redirige todo lo que imprima el script a un archivo de texto
    with open("D:\\Master\\TFM\\python\\resultados_evaluacion.txt", "w") as f:
        sys.stdout = f
        main()