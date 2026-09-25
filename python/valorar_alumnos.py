"""
Valorar soluciones de los alumnos - caso fintech stablecoins

Muestra el progreso por consola (igual que el script original de
MATLAB) y, ademas, genera un Excel por grupo con la tabla de
resultados y una leyenda.
"""

import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

# ==========================================================
# Configuracion
# ==========================================================
PATH_FICHEROS = r"D:\Master\TFM\DATOS"   # stablecoins.txt y stablecoinsOculta.txt viven aqui
PATH_ALUMNOS = r"D:\Master\TFM\Grupos"   # las carpetas de los grupos (Grupo1, Grupo2...) viven aqui
# el informe .xlsx de cada grupo se guarda DENTRO de la propia carpeta del grupo

COSTE_CUPON_2 = 2.85
NUM_CODIGOS_T1 = 3000
BENEFICIO_PCT_T1 = 0.01
BENEFICIO_PCT_T2 = 0.025

# columnas de la tabla de resultados, en este orden (igual que el informe de referencia)
COLUMNAS_TABLA = [
    "n2", "benefTot", "benef1", "benef2", "inver2", "ingresos2",
    "instalados2", "ratio2", "n1", "instalados1", "ratio1",
]

LEYENDA = [
    ("n2", "numero de cupones de tipo 2"),
    ("benefTot", "beneficio total"),
    ("benef1", "beneficio cupones tipo 1"),
    ("benef2", "beneficio cupones tipo 2"),
    ("inver2", "inversion en cupones tipo 2"),
    ("ingresos2", "ingreso derivado de los cupones tipo 2"),
    ("instalados2", "numero de clientes que instalan tipo 2"),
    ("ratio2", "porcentaje ofertas instalados en tipo 2"),
    ("n1", "numero de cupones de tipo 1"),
    ("instalados1", "numero de clientes que instalan tipo 1"),
    ("ratio1", "porcentaje ofertas instalados en tipo 1"),
]


# ==========================================================
# Funciones auxiliares
# ==========================================================

def get_subdirs(parent_dir):
    """Devuelve los nombres de las subcarpetas de primer nivel de parent_dir."""
    subdirs = []
    for name in os.listdir(parent_dir):
        ruta = os.path.join(parent_dir, name)  # Ruta incluyendo el nombre de la subcarpeta
        if os.path.isdir(ruta):  # Si es una carpeta, la añadimos a la lista
            subdirs.append(name)
    return subdirs


def leer_nombres_equipo(path_grupo):
    """Lee nombres.txt: primera linea = numero de equipo, resto = nombres."""

    # Abre nombres.txt y lo asigna a la variable f, con la garantía de que se cerrará 
    # automáticamente al salir del bloque
    with open(os.path.join(path_grupo, "nombres.txt"), encoding="utf-8") as f:
        #Recorre el fichero línea a línea quitando espacios en blanco y saltos de línea
        lineas = [linea.strip() for linea in f if linea.strip()] 
    num_equipo = lineas[0] if lineas else ""
    nombre_equipo = ", ".join(lineas[1:]) if len(lineas) > 1 else ""
    return num_equipo, nombre_equipo


def quitar_duplicados_internos(ids, nombre_conjunto):
    """
    Si una lista de ids tiene repetidos dentro de si misma, avisa por
    consola Y ADEMAS devuelve el texto del aviso (None si no habia
    duplicados), para que tambien pueda guardarse en el Excel.
    """
    ids_unicos = ids.drop_duplicates() #quita duplicados.
    n_duplicados = len(ids) - len(ids_unicos)
    aviso = None
    if n_duplicados > 0:
        aviso = f"{nombre_conjunto}: {n_duplicados} ids duplicados dentro de si mismo (eliminados)"
        print(f"Aviso: el {aviso}")
    return ids_unicos, aviso #devuelve la lista limpia y el texto del aviso (o None si no hubo duplicados)


def calcular_beneficio(ids1, ids2, sc_futuro, coste_cupon, pct_t1, pct_t2):
    """
    Calcula el beneficio real de una propuesta, comparandola con la
    tabla "verdad" sc_futuro (id, adoptado_futuro, gasto_futuro).
    """

    adoptan_futuro = sc_futuro.loc[sc_futuro["adoptado_futuro"] == 1, "id"]

    # --- Conjunto 1 (cupon gratis) ---
    ids1_adoptan = adoptan_futuro[adoptan_futuro.isin(ids1)]  # clientes a los que se les ofrecio el cupon 1 Y encima adoptaron
    gasto1 = sc_futuro.loc[sc_futuro["id"].isin(ids1_adoptan), "gasto_futuro"].sum() # suma del gasto total de los clientes que han recibido el cupon 1
    beneficio1 = pct_t1 * gasto1

    # --- Conjunto 2 (cupon de pago) ---
    if len(ids2) > 0:
        ids2_adoptan = adoptan_futuro[adoptan_futuro.isin(ids2)]
        gasto2 = sc_futuro.loc[sc_futuro["id"].isin(ids2_adoptan), "gasto_futuro"].sum()
        ingresos2 = pct_t2 * gasto2
        inversion2 = coste_cupon * len(ids2)  # el coste se paga por todos los que recibieron el cupon, adopten o no
        beneficio2 = ingresos2 - inversion2

    return {
        "n2": len(ids2),
        "benefTot": int(beneficio1) + (int(beneficio2) if len(ids2) > 0 else 0),
        "benef1": int(beneficio1),
        "benef2": int(beneficio2) if len(ids2) > 0 else 0,
        "inver2": int(inversion2) if len(ids2) > 0 else None,
        "ingresos2": int(ingresos2) if len(ids2) > 0 else None,
        "instalados2": len(ids2_adoptan) if len(ids2) > 0 else None,
        "ratio2": round(len(ids2_adoptan) / len(ids2), 2) if len(ids2) > 0 else None,
        "n1": len(ids1),
        "instalados1": len(ids1_adoptan),
        "ratio1": round(len(ids1_adoptan) / len(ids1), 2) if len(ids1) > 0 else None,
    }


def mostrar_beneficio(r):
    """Imprime los resultados de un escenario por consola"""
    print(f"\nBeneficio obtenido: {r['benefTot']} euros")
    print(f"Conjunto 1:\t{r['n1']} cupones ofrecidos, de los que {r['instalados1']} clientes lo adoptan")
    print(f"\tBeneficio obtenido conjunto 1: {r['benef1']} euros")

    print(f"Conjunto 2:\t{r['n2']} cupones ofrecidos", end="")
    if r["n2"] > 0:
        print(f", de los que {r['instalados2']} clientes lo adoptan")
        print(f"\tInversion conjunto 2: {r['inver2']} euros")
        print(f"\tIngresos conjunto 2: {r['ingresos2']} euros")
    else:
        print("")
    print(f"\tBeneficio obtenido conjunto 2: {r['benef2']} euros")


# ==========================================================
# Cargar datos
# ==========================================================

def leer_tabla(path):
    """Lee un fichero con separador ';' y coma decimal (formato real de
    los datos: 'id;adoptado;gasto_SC' con numeros tipo '163,95...')."""
    return pd.read_csv(path, sep=";", decimal=",")


def cargar_datos():
    stablecoins = leer_tabla(os.path.join(PATH_FICHEROS, "stablecoins.txt"))
    stablecoins_oculta = leer_tabla(os.path.join(PATH_FICHEROS, "stablecoinsOculta.txt"))

    # clientes que aun NO tienen stablecoins - son los "candidatos"
    candidatos = stablecoins.loc[stablecoins["adoptado"] == 0, "id"]

    # tabla "verdad" filtrada a esos candidatos
    stablecoins_futuro = stablecoins_oculta[stablecoins_oculta["id"].isin(candidatos)][
        ["id", "adoptado_futuro", "gasto_futuro"]
    ].reset_index(drop=True)

    return stablecoins, stablecoins_futuro


# ==========================================================
# Generar el informe Excel de un grupo
# ==========================================================

def generar_excel_grupo(path_salida, num_equipo, nombre_equipo, filas):
    """
    Crea un .xlsx con cabecera, datos del equipo, configuracion del
    problema, tabla de resultados (una fila por escenario, con sus
    avisos si los hubo) y una leyenda explicando cada columna.

    filas: lista de dicts, cada uno con las claves de COLUMNAS_TABLA
           mas 'escenario' (int) y 'avisos' (texto o None).
    """
    wb = Workbook() #Crea un libro Excel nuevo y vacío
    ws = wb.active #Todo libro Excel nuevo trae una hoja creada por defecto;
    # wb.active te da acceso a esa hoja para poder escribir en ella
    ws.title = f"G{num_equipo}"[:31]  # el nombre de hoja no puede pasar de 31 caracteres

    #Estilos de fuente
    fuente_normal = Font(name="Arial", size=10)
    fuente_titulo = Font(name="Arial", size=11, bold=True)
    fuente_cabecera = Font(name="Arial", size=10, bold=True)

    fila = 1 #Variable que lleva la cuenta de en qué fila se está escribiendo ahora mismo

    def escribir(col, texto, fuente=fuente_normal):
        celda = ws.cell(row=fila, column=col, value=texto) #accede (o crea) la celda en la fila actual
        #(NO HAY QUE INDICAR CUAL ES PORQUE ACCEDE A LA VARIABLE GLOBAL) y la columna indicada, y le pone el valor
        celda.font = fuente
        return celda

    # --- Cabecera ---
    escribir(1, "Configuracion del problema", fuente_titulo)
    fila += 1
    escribir(1, f"Valoracion de la solucion propuesta por el equipo {num_equipo}", fuente_titulo)
    fila += 2
    escribir(1, nombre_equipo)
    fila += 2

    escribir(1, f"Coste cupon tipo 1 0.00 Euros, porcentaje beneficio T1 {BENEFICIO_PCT_T1*100:.0f} por ciento")
    fila += 1
    escribir(1, f"Coste cupon tipo 2 {COSTE_CUPON_2:.2f} Euros, porcentaje beneficio T2 {BENEFICIO_PCT_T2*100:.2f} por ciento")
    fila += 2

    # --- Cabecera de la tabla ---
    for j, nombre_col in enumerate(COLUMNAS_TABLA, start=2):
        escribir(j, nombre_col, fuente_cabecera)
    escribir(len(COLUMNAS_TABLA) + 2, "avisos", fuente_cabecera)
    fila += 1

    # --- Una fila por escenario ---
    for f in filas:
        escribir(1, f"escenario {f['escenario']}")
        for j, nombre_col in enumerate(COLUMNAS_TABLA, start=2):
            valor = f.get(nombre_col) # obtiene el valor de la columna actual del diccionario f
            celda = ws.cell(row=fila, column=j, value=valor) # accede (o crea) la celda en la fila actual y columna j, y le pone el valor
            celda.font = fuente_normal
            if nombre_col in ("ratio1", "ratio2") and valor is not None:
                celda.number_format = "0%"
        escribir(len(COLUMNAS_TABLA) + 2, f.get("avisos") or "")
        fila += 1

    fila += 2

    # --- Leyenda ---
    escribir(1, "Leyenda", fuente_titulo)
    fila += 1
    for clave, descripcion in LEYENDA:
        escribir(1, clave, fuente_cabecera)
        escribir(2, descripcion)
        fila += 1

    # anchos de columna razonables
    ws.column_dimensions["A"].width = 20
    for col in range(2, len(COLUMNAS_TABLA) + 3):
        ws.column_dimensions[get_column_letter(col)].width = 13

    os.makedirs(path_salida, exist_ok=True)
    ruta_fichero = os.path.join(path_salida, f"G{num_equipo}_resultados.xlsx")
    wb.save(ruta_fichero)
    return ruta_fichero


# ==========================================================
# Programa principal
# ==========================================================

def main():
    print("Configuracion del problema")
    print(f"Coste cupon tipo 1: 0.00 euros, beneficio T1: {BENEFICIO_PCT_T1*100:.0f}%")
    print(f"Coste cupon tipo 2: {COSTE_CUPON_2:.2f} euros, beneficio T2: {BENEFICIO_PCT_T2*100:.2f}%")

    corte1a = 0
    corte1b = COSTE_CUPON_2 / BENEFICIO_PCT_T2
    corte2 = COSTE_CUPON_2 / (BENEFICIO_PCT_T2 - BENEFICIO_PCT_T1)
    print(f"a partir de {corte1a} euros de gasto: cupon 1 da beneficio (cupon 2 aun da perdidas)")
    print(f"a partir de {corte1b:.0f} euros de gasto: cupon 2 empieza a dar beneficio (pero menos que cupon 1)")
    print(f"a partir de {corte2:.0f} euros de gasto: cupon 2 da mas beneficio que cupon 1")

    stablecoins, stablecoins_futuro = cargar_datos() # Devuelve la tabla total de clientes y la tabla "verdad" filtrada a los candidatos
    ids_viejos = stablecoins.loc[stablecoins["adoptado"] == 1, "id"] # clientes que ya tenian stablecoins (no se les puede ofrecer cupones)

    grupos = get_subdirs(PATH_ALUMNOS) #devuelve la lista de nombres de carpeta que hay dentro de PATH_ALUMNOS — cada una es un grupo.
    print("\nDirectorios alumnos")
    if not grupos:
        print("Datos de los alumnos no encontrados")
    for i, g in enumerate(grupos, 1):
        print(f"Directorio #{i} = {g}")

    for grupo in grupos:
        path_grupo = os.path.join(PATH_ALUMNOS, grupo) #rurta completa a la carpeta del grupo
        num_equipo, nombre_equipo = leer_nombres_equipo(path_grupo) #lee su fichero nombres.txt
        print(f"\n\nValoracion de la solucion propuesta por el equipo {num_equipo}")
        print(nombre_equipo)

        escenarios = get_subdirs(path_grupo) #Lista las subcarpetas de escenario dentro de este grupo concreto
        filas_excel = [] #Lista vacía que irá acumulando el resultado de cada escenario de este grupo

        for es_idx, escenario in enumerate(escenarios, 1): #recorre la lista de escenarios dando un índice (1, 2, 3...) y el nombre de la carpeta de escenario
            print(f"escenario {es_idx}")
            path_sol = os.path.join(path_grupo, escenario)
            avisos = []

            ids1 = leer_tabla(os.path.join(path_sol, "cupones1.txt"))["id"] #Lee los dos ficheros de cupones de este escenario y se queda solo con la columna id de cada uno.
            ids2 = leer_tabla(os.path.join(path_sol, "cupones2.txt"))["id"]

            #VALIDACIONES
            # duplicados internos
            ids1, aviso1 = quitar_duplicados_internos(ids1, "conjunto 1")
            ids2, aviso2 = quitar_duplicados_internos(ids2, "conjunto 2")
            if aviso1:
                avisos.append(aviso1) #comprueba si hay algo que añadir; si lo hay, se añade a la lista avisos de este escenario con .append(...).
            if aviso2:
                avisos.append(aviso2)

            # clientes que ya tenian stablecoins, incluidos por error
            errores1 = ids1[ids1.isin(ids_viejos)] #filtra ids1 quedándose solo con los ids que también están en ids_viejos
            errores2 = ids2[ids2.isin(ids_viejos)]
            if len(errores1) > 0:
                msg = f"conjunto 1: {len(errores1)} clientes que ya tenian stablecoins (eliminados)"
                print(f"Error en el {msg}")
                avisos.append(msg)
                ids1 = ids1[~ids1.isin(errores1)] #filtra ids1 quedándose solo con los ids que NO están en errores1 (el ~ delante de .isin(...) invierte la condición)
            if len(errores2) > 0:
                msg = f"conjunto 2: {len(errores2)} clientes que ya tenian stablecoins (eliminados)"
                print(f"Error en el {msg}")
                avisos.append(msg)
                ids2 = ids2[~ids2.isin(errores2)]

            # ids repetidos entre conjunto 1 y conjunto 2
            duplicados_1_2 = ids1[ids1.isin(ids2)] #detecta ids que están en ambas listas
            if len(duplicados_1_2) > 0:
                msg = f"{len(duplicados_1_2)} ids repetidos en 1 y 2 (eliminados de ambos)"
                print(f"Aviso: {msg}")
                avisos.append(msg)
                #los quita de AMBOS conjuntos.
                ids1 = ids1[~ids1.isin(duplicados_1_2)] 
                ids2 = ids2[~ids2.isin(duplicados_1_2)]

            print(f"En el conjunto 1 hay {len(ids1)} clientes")
            print(f"En el conjunto 2 hay {len(ids2)} clientes")

            # limite de cupones tipo 1
            if len(ids1) > NUM_CODIGOS_T1:
                msg = f"conjunto 1 truncado de {len(ids1)} a {NUM_CODIGOS_T1} clientes (maximo permitido)"
                print(f"El {msg}")
                avisos.append(msg)
                ids1 = ids1.iloc[:NUM_CODIGOS_T1]

            #CALCULO DEL BENEFICIO REAL DE LA PROPUESTA
            resultado = calcular_beneficio(
                ids1, ids2, stablecoins_futuro, COSTE_CUPON_2, BENEFICIO_PCT_T1, BENEFICIO_PCT_T2
            )
            mostrar_beneficio(resultado)

            resultado["escenario"] = es_idx #añadir una etiqueta nueva llamada "escenario" y darle el valor del indice en el que estemos
            resultado["avisos"] = "; ".join(avisos) if avisos else None #añadir otra etiqueta llamada "avisos"
            filas_excel.append(resultado) #filas_excel es la lista que se creó antes y que va acumulando todos los escenarios de este grupo, uno detrás de otro
            #Una vez que tiene todos los escenarios del grupo dentro, es lo que se pasa a la función generar_excel_grupo(...) 

        ruta_excel = generar_excel_grupo(path_grupo, num_equipo, nombre_equipo, filas_excel)
        print(f"\nInforme Excel generado: {ruta_excel}")

    print("\nfin")


if __name__ == "__main__":
    main()