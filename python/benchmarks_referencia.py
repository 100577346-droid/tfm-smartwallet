"""
Benchmarks de referencia - caso fintech stablecoins

Calcula puntos de referencia con los que comparar sus resultados.

Modo 1 - Escenarios basicos sin modelo:
    Escenario 1: reparto aleatorio, solo cupon 1
    Escenario 2: reparto aleatorio, cupon 1 + cupon 2 con n2 creciente
    Escenario 3: reparto "vidente" - conociendo el futuro real
                 (cota superior teorica: el maximo beneficio posible)


Modo 2 - Modelo simple sin machine learning:
    Estima el gasto futuro de cada cliente como proporcional a su
    renta, asumiendo que todos adoptan (no intenta predecir quién va a adoptar y quién no. 
    Trata a todos los clientes candidatos como si fueran a adoptar con seguridad. 
    Luego, cuando se compara el resultado contra la realidad, los que en verdad no adoptan 
    simplemente no aportan ningún beneficio). Con esa estimación de gasto (aunque sea aproximada) 
    para cada cliente, decide como repartir los cupones. Ambos modos reutilizan la carga de datos 
    y el calculo de beneficio

Modo 3 - Modo conservador: solo clientes con transferencias internacionales
    No estima ningun gasto en stablecoins. 
    Se ofrece el cupon 1 (gratis) directamente a los clientes que YA realizan transferencias
    internacionales (dato visible en transacciones.txt); si hay mas candidatos que cupones tipo 1 
    disponibles, se prioriza a los que mas remesan. No se ofrece cupon 2 en este modelo, ya que el volumen
    remesado no es una estimacion de gasto en stablecoins y no tiene sentido compararlo contra los umbrales corte1a/corte1b/corte2.    
"""

import numpy as np
import pandas as pd
 
#Importa constantes y funciones directamente desde el otro fichero, en vez de duplicarlas
from valorar_alumnos import (
    PATH_FICHEROS, COSTE_CUPON_2, NUM_CODIGOS_T1, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2,
    leer_tabla, cargar_datos, calcular_beneficio,
)
 
# NOTA: PATH_FICHEROS se importa desde valorar_alumnos.py, no se define aqui.
# Ahi es donde hay que apuntarlo a la carpeta de datos, por ejemplo:
#     PATH_FICHEROS = r"D:\Master\TFM\DATOS"
# Este script (benchmarks.py) puedes guardarlo en D:\Master\TFM\Python;
# la ruta de los datos (transacciones.txt, stablecoins.txt) se sigue
# controlando desde valorar_alumnos.py.
 
SEMILLA_ALEATORIA = 1992  # misma semilla que se usa en el resto del TFM (R, RapidMiner)
 
 
# ==========================================================
# Puntos de corte del gasto (identicos a los de valorar_alumnos)
# ==========================================================
 
def calcular_cortes(coste_cupon2, pct_t1, pct_t2):
    corte1a = 0
    # Para que sea rentable el cupon 2 tiene que cumplirse:
    # gasto * beneficioPercentT2 > costeCupon2 => gasto>costeCupon2/beneficioPercentT2
    corte1b = coste_cupon2 / pct_t2 # el cupón 2 empieza a ser rentable (aunque el 1 siga siendo mejor)
    #gasto * beneficioPercentT2 - costeCupon2 > gasto * beneficioPercentT1 =>
    # gasto > costeCupon2 / (beneficioPercentT2 - beneficioPercentT1)
    corte2 = coste_cupon2 / (pct_t2 - pct_t1) #a partir de él, el cupón 2 es siempre más rentable
    return corte1a, corte1b, corte2
 
 
# ==========================================================
# Reparto optimo entre cupon 1 y cupon 2, dado un gasto estimado
# ==========================================================
 
def repartir_en_tipo1_tipo2(df_pred, coste_cupon2, pct_t1, pct_t2, num_codigos_t1, corte1a, corte1b, corte2):
    """
    df_pred: DataFrame con columnas 'id', 'adoptado_futuro', 'gasto_futuro'
             (puede ser el dato real o una estimacion).
    Decide a quién dar cada cupón (Devuelve (ids1, ids2))
    """
    #Se queda solo con los que (según df_pred) van a adoptar, y los ordena de mayor a menor gasto.
    candidatos = df_pred[df_pred["adoptado_futuro"] == 1].sort_values("gasto_futuro", ascending=False)
 
    #Divide a los candidatos en tres franjas según los umbrales: 
    benef2 = candidatos[candidatos["gasto_futuro"] > corte2] # Es una tabla con todas las filas de candidatos donde el gasto estimado supera corte2.
    # Como viene de candidatos (que tenía columnas id, adoptado_futuro, gasto_futuro), benef2 sigue teniendo esas mismas columnas.
    benef1b = candidatos[(candidatos["gasto_futuro"] > corte1b) & (candidatos["gasto_futuro"] <= corte2)] #mejor con cupón 1, pero el 2 también compensa
    benef1a = candidatos[(candidatos["gasto_futuro"] > corte1a) & (candidatos["gasto_futuro"] <= corte1b)] #solo compensa el cupón 1
 
    #Todos los de la franja superior van directos al cupón 2:
    ids2 = benef2["id"].copy() #selecciona solo la columna id de la tabla benef2, descartando las otras dos columnas.
 
    # Hay límite de cupones tipo 1. 
 
    #Hay suficientes candidatos en la franja intermedia para llenar el cupo de cupones tipo 1
    if len(benef1b) >= num_codigos_t1:  
        # a los que menos gastan dentro del rango 1b se les da cupon 1
        # (es donde la ventaja relativa del cupon gratis es mayor)
        ids1 = benef1b["id"].iloc[-num_codigos_t1:]
        # a los que mas gastan dentro de ese mismo rango se les sube a cupon 2
        # (porque el cupon 2 da más ingresos cuanto mayor es el gasato (el un 2,5% del gasto))
        ids2 = pd.concat([ids2, benef1b["id"].iloc[:len(benef1b) - num_codigos_t1]])
 
    # si el rango 1b no llega a completar el cupo
    elif len(benef1a) >= num_codigos_t1 - len(benef1b):
        # benef1b no llega a completar el cupo por si sola, pero TODOS sus
        # clientes dan mas beneficio que cualquier cliente de benef1a
        # (mismo 1%, pero sobre un gasto mayor) -> se aprovechan primero los benef1b, 
        # y solo se completa lo que falte con los mejores de benef1a
        faltan = num_codigos_t1 - len(benef1b)
        ids1 = pd.concat([benef1b["id"], benef1a["id"].iloc[:faltan]])
    else:
        # no hay suficientes candidatos ni en 1a ni en 1b para llenar el cupo
        #junta todos los clientes de benef1b con todos los de benef1a, sin limitar la cantidad
        ids1 = pd.concat([benef1b["id"], benef1a["id"]])
 
    return ids1.reset_index(drop=True), ids2.reset_index(drop=True)
 
 
# ==========================================================
# Mostrar resultados
# ==========================================================
 
def mostrar_tabla_resultados(resultados):
    """resultados: lista de dicts, cada uno con 'nombre' + las claves de calcular_beneficio."""
    print(f"{'Escenario':<28}{'n2':>8}{'benefTot':>12}{'benef1':>10}{'benef2':>10}{'n1':>8}{'instalados1':>13}")
    for r in resultados:
        print(f"{r['nombre']:<28}{r['n2']:>8}{r['benefTot']:>12}{r['benef1']:>10}{r['benef2']:>10}{r['n1']:>8}{r['instalados1']:>13}")
 
 
# ==========================================================
# Guardar resultados en CSV
# ==========================================================
 
def guardar_resultados_csv(resultados, path_salida="resultados_benchmarks.csv"):
    """
    resultados: lista de dicts (cada uno con 'nombre' + las claves de calcular_beneficio,
    y opcionalmente claves extra como 'ratio_estimado' o 'n_candidatos').
 
    Al venir de modos distintos, no todos los dicts tienen exactamente las
    mismas claves; pandas rellena con NaN las columnas que no apliquen a
    una fila concreta, así que no hace falta unificar nada a mano.
    """
    df_resultados = pd.DataFrame(resultados)
    df_resultados.to_csv(path_salida, index=False, encoding="utf-8-sig")
    print(f"\nResultados guardados en: {path_salida}")
 
 
# ==========================================================
# MODO 1 - Escenarios basicos sin modelo
# ==========================================================
 
def modo1_escenarios_basicos(stablecoins, stablecoins_futuro, rng):
    #rng (el generador de números aleatorios ya creado fuera, con la semilla fija)
    resultados = [] #Crea una lista vacía donde se irán guardando los resultados de cada escenario
    corte1a, corte1b, corte2 = calcular_cortes(COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2)
 
    candidatos = stablecoins.loc[stablecoins["adoptado"] == 0, "id"] #Filtra la tabla stablecoins quedándose 
    # solo con los ids de los clientes que todavía no tienen stablecoins
 
    # --- Escenario 1: reparto aleatorio, solo cupon 1 ---
    ids1 = pd.Series(rng.choice(candidatos, size=NUM_CODIGOS_T1, replace=False))
    #elige al azar NUM_CODIGOS_T1 ids de la lista candidatos, sin repetir ninguno. 
    ids2 = pd.Series([], dtype=ids1.dtype) #Crea una lista vacía para el cupón 2 — en este escenario no se ofrece ningún cupón de pago.
    r = calcular_beneficio(ids1, ids2, stablecoins_futuro, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2)
    r["nombre"] = "1. Aleatorio (solo cupon 1)"
    resultados.append(r)
 
    # --- Escenario 2: reparto aleatorio, cupon 1 + cupon 2 con n2 creciente ---
    n2_valores = [1000, 5000, 20000, 50000, 100000] #Lista de tamaños distintos de cupón 2 a probar
    for i, n2 in enumerate(n2_valores, 1): #dando en cada vuelta: i (el número de vuelta, empezando en 1) y n2 (el valor de esa posición).
        seleccion = pd.Series(rng.choice(candidatos, size=NUM_CODIGOS_T1 + n2, replace=False))
        ids1 = seleccion.iloc[:NUM_CODIGOS_T1]
        ids2 = seleccion.iloc[NUM_CODIGOS_T1:]
        r = calcular_beneficio(ids1, ids2, stablecoins_futuro, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2)
        r["nombre"] = f"2.{i} Aleatorio (n2={n2})"
        resultados.append(r)
 
    # --- Escenario 3: reparto "vidente" - conociendo el futuro real ---
    # Se reparte usando directamente stablecoins_futuro (la tabla que normalmente está "oculta", reservada para validar)
    # Con esos datos, ordena por gasto_futuro, filtra por adoptado_futuro == 1, reparte según los umbrales). 
    # Al alimentarla con la verdad, el reparto que produce es automáticamente el óptimo real posible (cota superior teorica).
    ids1, ids2 = repartir_en_tipo1_tipo2(
        stablecoins_futuro, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2,
        NUM_CODIGOS_T1, corte1a, corte1b, corte2,
    )
    r = calcular_beneficio(ids1, ids2, stablecoins_futuro, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2)
    r["nombre"] = "3. Vidente (cota superior teorica)"
    resultados.append(r)
 
    return resultados
 
 
# ==========================================================
# MODO 2 - Modelo simple: gasto proporcional a los ingresos
#           transaccionales (categoria 'Ingreso' en transacciones.txt)
# ==========================================================
 
def cargar_ingresos_agregados(path_ficheros):
    """
    Lee transacciones.txt y agrega, por cliente, el importe total de las
    transacciones de tipo 'Ingreso'. 
 
    """
    transacciones = leer_tabla(f"{path_ficheros}\\transacciones.txt")
    transacciones = transacciones.rename(columns={"idCliente": "id"}) #Cambia el nombre de la columna idCliente a id (para poder cruzarlo constablecoins.txt)
    ingresos = transacciones[transacciones["tipo"] == "Ingreso"]
    ingresos_agregados = ingresos.groupby("id", as_index=False)["importe"].sum() #Sumar los ingresospor cliente
    ingresos_agregados = ingresos_agregados.rename(columns={"importe": "ingreso_total"})
    return ingresos_agregados
 
 
def estimar_ratio_ingresos(stablecoins, ingresos_agregados):
    """
    Estima el ratio gasto_SC/ingreso_total a partir de los clientes que YA han adoptado (datos visibles)
    """
    adoptantes = stablecoins.merge(ingresos_agregados, on="id") #Combina las dos tablas (para añadir la coluna de ingreso_total a la tabla stablecoins)
    adoptantes = adoptantes[(adoptantes["adoptado"] == 1) & (adoptantes["ingreso_total"] > 0)]
    ratio = (adoptantes["gasto_SC"] / adoptantes["ingreso_total"]).mean()
    return ratio
 
 
def modo2_proporcional_ingresos(stablecoins, stablecoins_futuro, ingresos_agregados):
    """
    Recibe tres tablas:
    stablecoins (datos visibles)
    stablecoins_futuro (la "verdad" con la que se valida el resultado)
    ingresos_agregados (la tabla id/ingreso_total)
 
    """
    corte1a, corte1b, corte2 = calcular_cortes(COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2)
 
    ratio_estimado = estimar_ratio_ingresos(stablecoins, ingresos_agregados)
 
    proxy_gasto = ingresos_agregados.copy() #Copia la tabla de ingresos, para no modificar accidentalmente la original al añadirle columnas nuevas.
    proxy_gasto["gasto_futuro"] = proxy_gasto["ingreso_total"] * ratio_estimado # Crea una nueva columna gasto_futuro= ingreso de cada cliente * el ratio estimado
    proxy_gasto["adoptado_futuro"] = 1  # como este modelo no sabe predecir quién va a adoptar, asume que todos adoptan
 
    df_pred = proxy_gasto[["id", "adoptado_futuro", "gasto_futuro"]] #Quedarse solo con las columnas necesarias
 
    #Le pasa la tabla estimada (no la real)
    ids1, ids2 = repartir_en_tipo1_tipo2(
        df_pred, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2,
        NUM_CODIGOS_T1, corte1a, corte1b, corte2,
    )
 
    r = calcular_beneficio(ids1, ids2, stablecoins_futuro, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2)
    r["nombre"] = "Proporcional a ingresos (sin ML)"
    r["ratio_estimado"] = ratio_estimado
    return r
 
 
 
# ==========================================================
# MODO 3 - Solo clientes con transferencias internacionales
# ==========================================================
 
def cargar_transferencias_internacionales(path_ficheros):
    """
    Lee transacciones.txt y agrega, por cliente, el importe total de
    transacciones de tipo 'Transferencia_Internacional'. Solo apareceran
    en el resultado los clientes que tengan al menos una.
    """
    transacciones = leer_tabla(f"{path_ficheros}\\transacciones.txt")
    transacciones = transacciones.rename(columns={"idCliente": "id"}) #para poder cruzarla después con stablecoins.txt
    remesas = transacciones[transacciones["tipo"] == "Transferencia Internacional"]
    remesas_agregadas = remesas.groupby("id", as_index=False)["importe"].sum() #Agrupa por cliente y suma el importe de cada uno
    remesas_agregadas = remesas_agregadas.rename(columns={"importe": "remesas_total"})
    return remesas_agregadas
 
 
def modo3_transferencias_internacionales(stablecoins, stablecoins_futuro, remesas_agregadas):
    """
    Regla de negocio muy simple: se ofrece el cupon 1 (gratis) a los
    clientes que YA realizan transferencias internacionales -- sin
    intentar traducir el volumen remesado a un gasto estimado en
    stablecoins (serian magnitudes distintas y no tiene sentido
    compararlas contra corte1a/corte1b/corte2, que estan en euros de
    gasto en stablecoins). Si hay mas candidatos que cupones tipo 1
    disponibles, se prioriza a los que mas remesan. No se ofrece
    cupon 2 en este modelo.
    """
    candidatos_ordenados = remesas_agregadas.sort_values("remesas_total", ascending=False) #de mayor a menor volumen remesado
 
    ids1 = candidatos_ordenados["id"].iloc[:NUM_CODIGOS_T1].reset_index(drop=True) #Coge los primeros NUM_CODIGOS_T1 para el cupón 1
    ids2 = pd.Series([], dtype=ids1.dtype)
 
    r = calcular_beneficio(ids1, ids2, stablecoins_futuro, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2)
    r["nombre"] = "Solo transferencias internacionales (cupon 1)"
    r["n_candidatos"] = len(remesas_agregadas)
    return r
 
 
# ==========================================================
# Programa principal
# ==========================================================
 
def main():
    rng = np.random.default_rng(SEMILLA_ALEATORIA) #Crea el generador de números aleatorios con la semilla fija (1992)
 
    stablecoins, stablecoins_futuro = cargar_datos()
 
    todos_resultados = []  # aqui se van acumulando los resultados de los 3 modos, para el CSV final
 
    print("=== MODO 1: escenarios basicos sin modelo ===\n")
    resultados_modo1 = modo1_escenarios_basicos(stablecoins, stablecoins_futuro, rng)
    mostrar_tabla_resultados(resultados_modo1)
    todos_resultados.extend(resultados_modo1)
 
    print("\n=== MODO 2: modelo simple, gasto proporcional a los ingresos ===\n")
    try:
        ingresos_agregados = cargar_ingresos_agregados(PATH_FICHEROS) #Carga y agrega los ingresos desde transacciones.txt
        resultado_modo2 = modo2_proporcional_ingresos(stablecoins, stablecoins_futuro, ingresos_agregados) #Ejecuta el modo 2 con esos ingresos agregados.
        print(f"Ratio gasto/ingreso estimado a partir de los adoptantes visibles: {resultado_modo2['ratio_estimado']:.5f}")
        mostrar_tabla_resultados([resultado_modo2])
        todos_resultados.append(resultado_modo2)
    except FileNotFoundError:
        print("No se encuentra transacciones.txt en PATH_FICHEROS: el modo 2 necesita")
        print("agregar el importe de las transacciones de tipo 'Ingreso' por cliente.")
 
    print("\n=== MODO 3: solo clientes con transferencias internacionales ===\n")
    try:
        remesas_agregadas = cargar_transferencias_internacionales(PATH_FICHEROS) #carga y agrega las remesas desde transacciones.txt    
        resultado_modo3 = modo3_transferencias_internacionales(stablecoins, stablecoins_futuro, remesas_agregadas)
        print(f"Clientes candidatos (con transferencias internacionales): {resultado_modo3['n_candidatos']}")
        mostrar_tabla_resultados([resultado_modo3])
        todos_resultados.append(resultado_modo3)
    except FileNotFoundError:
        print("No se encuentra transacciones.txt en PATH_FICHEROS: el modo 3 necesita")
        print("agregar el importe de las transacciones de tipo 'Transferencia_Internacional' por cliente.")
 
    # Guarda todos los resultados (de los 3 modos) juntos en un unico CSV,
    # en la misma carpeta donde vive este script (D:\Master\TFM\Python)
    PATH_SALIDA_RESULTADOS = r"D:\Master\TFM\Python"
    guardar_resultados_csv(todos_resultados, path_salida=f"{PATH_SALIDA_RESULTADOS}\\resultados_benchmarks.csv")
 
 
if __name__ == "__main__":
    main()