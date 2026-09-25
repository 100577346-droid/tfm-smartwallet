import pandas as pd
import numpy as np

# =============================================================================
# CARGA DE DATOS
# =============================================================================
PATH = r'D:\Master\TFM\DATOS' + '\\'

# OJO: dtype={'cp': str} asegura que el cp se lea como texto (no pierde ceros
# a la izquierda) MIENTRAS trabajamos en este script. Pero al escribir a CSV,
# el tipo no se guarda como metadato: si tú u otra persona vuelve a abrir
# union_dataset.csv (aquí, en RapidMiner, en Excel...) SIN indicar de nuevo
# que 'cp' es texto/nominal, se perderán los ceros a la izquierda otra vez.
clientes = pd.read_csv(PATH + 'clientes.txt', sep=';', decimal=',', dtype={'cp': str})
transacciones = pd.read_csv(PATH + 'transacciones.txt', sep=';', decimal=',')
stablecoins   = pd.read_csv(PATH + 'stablecoins.txt', sep=';', decimal=',')

# Guardamos todas las columnas de clientes (incluido idCliente)
columnas_origen_clientes = list(clientes.columns)

# =============================================================================
# PASO 1. SEPARAR INGRESOS Y GASTOS (TRANSACCIONES)
# =============================================================================
ingresos_df = transacciones[transacciones['tipo'] == 'Ingreso'].copy()
gastos_df   = transacciones[transacciones['tipo'] != 'Ingreso'].copy()

# =============================================================================
# PASO 2. AGREGAR DATOS POR CLIENTE (UNA FILA POR CLIENTE)
# =============================================================================
# 2.1 Suma de ingresos
resumen_ingresos = ingresos_df.groupby('idCliente')['importe'].sum().reset_index()
resumen_ingresos.columns = ['idCliente', 'suma_ingresos']

# 2.2 Gastos básicos
resumen_gastos = gastos_df.groupby('idCliente').agg(
    suma_gastos           = ('importe', 'sum'),
    num_movimientos_gasto = ('importe', 'count')
).reset_index()

# 2.3 Gasto desglosado por categoría
gasto_por_categoria = gastos_df.pivot_table(
    index='idCliente',
    columns='tipo',
    values='importe',
    aggfunc='sum',
    fill_value=0
).reset_index()
gasto_por_categoria.columns = [
    f'gasto_{col}' if col != 'idCliente' else col
    for col in gasto_por_categoria.columns
]

# Limpiamos los nombres de categoría que traen espacios (ej. "Ocio Nocturno",
# "Transferencia Internacional") para que no den problemas al referenciarlos
# como atributos en RapidMiner o en fórmulas/macros más adelante.
gasto_por_categoria.columns = [
    col.replace(' ', '_') for col in gasto_por_categoria.columns
]

# =============================================================================
# PASO 3. CRUCE FINAL
# =============================================================================
df_final = clientes.copy()

df_final = df_final.merge(resumen_ingresos,   on='idCliente', how='left')
df_final = df_final.merge(resumen_gastos,      on='idCliente', how='left')
df_final = df_final.merge(gasto_por_categoria, on='idCliente', how='left')
df_final = df_final.merge(
    stablecoins.rename(columns={'id': 'idCliente'}),
    on='idCliente', how='left'
)

# =============================================================================
# PASO 4. TRATAMIENTO DE NULOS
# =============================================================================
df_final['suma_ingresos']         = df_final['suma_ingresos'].fillna(0)
df_final['suma_gastos']           = df_final['suma_gastos'].fillna(0)
df_final['num_movimientos_gasto'] = df_final['num_movimientos_gasto'].fillna(0).astype(int)

columnas_gasto = [col for col in df_final.columns if col.startswith('gasto_') and col != 'gasto_SC']
df_final[columnas_gasto] = df_final[columnas_gasto].fillna(0)
df_final['gasto_SC']     = df_final['gasto_SC'].fillna(0)

# =============================================================================
# PASO 4b. VARIABLES ADICIONALES (para no perder matices en el modelado)
# =============================================================================
# suma_ingresos = 0 puede significar "no tiene nómina/prestación domiciliada
# ese trimestre", no necesariamente "sin ingresos" (p. ej. rentistas o
# jubilados sin prestación en T_Nominas/T_Prestaciones). Esta bandera deja
# ese matiz disponible para el modelo en vez de perderlo en el 0.
df_final['tiene_ingresos_declarados'] = (df_final['suma_ingresos'] > 0).astype(int)

# numero_hijos = 0 ya lo tenemos, pero edad_hijo_mayor es NaN cuando no hay
# hijos. Esta bandera es más limpia de usar como input que rellenar el NaN.
df_final['tiene_hijos'] = (df_final['numero_hijos'] > 0).astype(int)

# =============================================================================
# PASO 5. REORDENAR Y EXPORTAR
# =============================================================================
columnas_transacciones = [
    'suma_ingresos', 'tiene_ingresos_declarados',
    'suma_gastos', 'num_movimientos_gasto'
] + columnas_gasto

columnas_stablecoins = ['adoptado', 'gasto_SC']

orden_final_columnas = (
    columnas_origen_clientes
    + ['tiene_hijos']
    + columnas_transacciones
    + columnas_stablecoins
)
df_final = df_final[orden_final_columnas]

df_final.to_csv(PATH + 'union_dataset.csv', sep=';', decimal=',', index=False)
print('union_dataset.csv creado correctamente')