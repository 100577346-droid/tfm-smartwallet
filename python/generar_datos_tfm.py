"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        GENERADOR DE DATOS SINTÉTICOS PARA TFM - SMART WALLET                 ║
║        LUCÍA LIAÑO GONZÁLEZ                                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


import numpy as np #operaciones matemáticas y generación de números aleatorios
import pandas as pd #creación y manipulación de tablas
import os

# =============================================================================
# CONFIG
# =============================================================================
PATH_FICHEROS = r'D:\Master\TFM\DATOS' + os.sep

np.random.seed(42)  # Fija la "semilla" del generador de números aleatorios. 
#Útil para reproducibilidad


# =============================================================================
# PARTE 1. CREAR CLIENTES
# =============================================================================

N_CLIENTES = 300_000
id_clientes = np.arange(N_CLIENTES) 


# ─────────────────────────────────────────────────────────────────────────────
# EDAD
# ─────────────────────────────────────────────────────────────────────────────
poblacion = pd.read_excel(os.path.join(PATH_FICHEROS, 'poblacionPorEdad.xlsx'))
edades_raw = poblacion['Edad'].values.astype(int)
probs_raw  = poblacion['Probabilidad'].values.astype(float)

es_adulto           = edades_raw >= 18 # Crea un array booleano 
edades_posibles     = edades_raw[es_adulto] #selecciona solo los elementos donde es_adulto sea True
probs_adultos       = probs_raw[es_adulto]
probs_adultos       = probs_adultos / probs_adultos.sum()   # normalizar

edad = np.random.choice(edades_posibles, size=N_CLIENTES, replace=True, p=probs_adultos)
#array de 300.000 edades siguiendo la distribución del INE


# ─────────────────────────────────────────────────────────────────────────────
# CÓDIGO POSTAL
# ─────────────────────────────────────────────────────────────────────────────
t_irpf = pd.read_excel(
    PATH_FICHEROS + 'RentaPorDP.xlsx',
    usecols='A:E',          
    header=0,
    dtype={'CP': str} # Conserva los ceros a la izquierda
)

pesos_cp = t_irpf['nDeclaraciones'].values.astype(float)
pesos_cp = pesos_cp / pesos_cp.sum()

cp = np.random.choice(t_irpf['CP'].values, size=N_CLIENTES, replace=True, p=pesos_cp)


# ─────────────────────────────────────────────────────────────────────────────
# LATITUD, LONGITUD E INGRESOS BASE
# ─────────────────────────────────────────────────────────────────────────────
# Ir al Excel, coger la información del barrio y pegársela al cliente
cp_to_idx = {v: i for i, v in enumerate(t_irpf['CP'].values)} #Crea un índice que da a cada CP su fila
idx_cp    = np.array([cp_to_idx[c] for c in cp]) #asigna a cada cliente su fila segun su CP

latitud_hogar  = t_irpf['Lat_Centro'].values[idx_cp]  + (np.random.rand(N_CLIENTES) - 0.5) * 0.01
longitud_hogar = t_irpf['Lon_Centro'].values[idx_cp]  + (np.random.rand(N_CLIENTES) - 0.5) * 0.01
ingresos_base  = t_irpf['renta'].values[idx_cp] / t_irpf['nDeclaraciones'].values[idx_cp] 
# Renta media del barrio = renta total del CP / número de declaraciones del CP


# ─────────────────────────────────────────────────────────────────────────────
# INGRESOS ANUALES
# ─────────────────────────────────────────────────────────────────────────────
ingresos = ingresos_base + 0.1 * ingresos_base * np.random.randn(N_CLIENTES)
# Resultado: ingresos individuales = media del barrio + ruido del ±10% respecto del ingreso medio del barrio
ingresos = np.maximum(ingresos, 12_000) #(Salario Mínimo)


# ─────────────────────────────────────────────────────────────────────────────
# TIPO DE EMPELO
# ─────────────────────────────────────────────────────────────────────────────
lista_empleo = ['cuenta ajena', 'parado', 'autonomo', 'no trabaja']
# Cuenta ajena: 44.69% | Parado: 5.85% | Autónomo: 8.4% | No trabaja: 41.06%
distri_empleo = [0.4469, 0.0585, 0.084, 0.4106]
tipo_empleo = np.random.choice(lista_empleo, size=N_CLIENTES, replace=True, p=distri_empleo)


# ─────────────────────────────────────────────────────────────────────────────
# NIVEL DE ESTUDIOS
# ─────────────────────────────────────────────────────────────────────────────
lista_estudios = ['Primarios', 'Secundarios', 'Grado', 'Postgrado']
media_renta    = ingresos_base.mean()

nivel_estudios = np.empty(N_CLIENTES, dtype=object)
# dtype=object → permite almacenar strings de longitud variable
zona_alta = ingresos_base > media_renta 
#arrays booleanos donde True es para clientes en barrios con renta superior a la media
zona_baja = ~zona_alta

# Zona de renta alta
n_alta = zona_alta.sum()  #.sum() sobre un array booleano cuenta cuántos True hay (False=0)
nivel_estudios[zona_alta] = np.random.choice(
    lista_estudios, size=n_alta, replace=True, p=[0.05, 0.15, 0.50, 0.30]
    # Distribución sesgada hacia estudios superiores
)
# Zona de renta baja
n_baja = zona_baja.sum()
nivel_estudios[zona_baja] = np.random.choice(
    lista_estudios, size=n_baja, replace=True, p=[0.30, 0.40, 0.20, 0.10]
)


# ─────────────────────────────────────────────────────────────────────────────
# USO DE FINTECH
# ─────────────────────────────────────────────────────────────────────────────
p_fintech = np.full(N_CLIENTES, 0.2) # array donde todos los elementos son 0.2
p_fintech[edad < 35] += 0.3
estudios_sup = np.isin(nivel_estudios, ['Grado', 'Postgrado']) 
#devuelve True cuando el elemento (nivel_estudios) está en la lista (Grado, Postgrado)
p_fintech[estudios_sup] += 0.3
p_fintech = np.minimum(p_fintech, 1.0)
usa_fintech = (np.random.rand(N_CLIENTES) < p_fintech).astype(int)
# np.random.rand() genera un número aleatorio Uniforme[0,1) por cliente.
# Si ese número es menor que su probabilidad p_fintech → usa fintech =1(True)


# ─────────────────────────────────────────────────────────────────────────────
# HIPOTECA
# ─────────────────────────────────────────────────────────────────────────────
lista_h  = np.arange(0, 31) * 10_000
pesos_h  = np.array([
    0.70,
    0.005, 0.005, 0.01, 0.01, 0.01, 0.01, 0.01,
    0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.04,
    0.045, 0.05, 0.04, 0.03, 0.02, 0.01,
    0.005, 0.005, 0.004, 0.003, 0.002, 0.001,
    0.001, 0.001, 0.001, 0.001
])
pesos_h = pesos_h / pesos_h.sum()
# Asignamos el importe hipotecario a cada cliente según los pesos:
hipoteca_imp_inicial = np.random.choice(lista_h, size=N_CLIENTES, replace=True, p=pesos_h)
hipoteca_imp_inicial[edad > 70] = 0


# ─────────────────────────────────────────────────────────────────────────────
# IMPAGO DE HIPOTECA
# ─────────────────────────────────────────────────────────────────────────────
cuota_estimada  = hipoteca_imp_inicial * 0.006 # Estimación de la cuota mensual: 0.6% del capital total
sueldo_mensual  = ingresos / 12
ratio_esfuerzo  = np.where(sueldo_mensual > 0, cuota_estimada / sueldo_mensual, 0)
#ratio_esfuerzo = cuota_estimada / sueldo_mensual pero con protección extra contra divisiones por cero

prob_impago = np.full(N_CLIENTES, 0.02)
prob_impago[ratio_esfuerzo > 0.40] = 0.15
idx_paro_riesgo = (tipo_empleo == 'parado') & (ratio_esfuerzo > 0.40)
prob_impago[idx_paro_riesgo] = 0.30

hipoteca_impagada = (
    (np.random.rand(N_CLIENTES) < prob_impago) & (hipoteca_imp_inicial > 0)
).astype(int)

# ─────────────────────────────────────────────────────────────────────────────
# HIJOS
# ─────────────────────────────────────────────────────────────────────────────
lista_hijos  = np.arange(8)
distri_hijos = np.array([0.4202, 0.2521, 0.1681, 0.0840, 0.0420, 0.0210, 0.0084, 0.0042])
distri_hijos = distri_hijos / distri_hijos.sum()

# Asignamos número de hijos siguiendo la distribución:
numero_hijos = np.random.choice(lista_hijos, size=N_CLIENTES, replace=True, p=distri_hijos)
#Hacemos alguna modificacion 
numero_hijos[edad <= 22] = 0
numero_hijos[(edad <= 25) & (numero_hijos >= 2)] = 2
numero_hijos[(edad <= 30) & (numero_hijos >= 4)] = 3


# ─────────────────────────────────────────────────────────────────────────────
# EDAD DEL HIJO MAYOR
# ─────────────────────────────────────────────────────────────────────────────
# Distribución de probabilidad de la edad al tener el primer hijo (18-50 años) según estadísticas del INE:
pesos_doc = np.array([
    0.008, 0.013, 0.016, 0.020, 0.021,
    0.024, 0.028, 0.030, 0.033, 0.039, 0.044, 0.051,
    0.060, 0.069, 0.073, 0.072, 0.069,
    0.064, 0.056, 0.047, 0.038, 0.031,
    0.025, 0.018, 0.014, 0.009, 0.006, 0.004,
    0.003, 0.002, 0.001, 0.001, 0.000
])
pesos_doc = pesos_doc / pesos_doc.sum()
edades_parto = np.random.choice(np.arange(18, 51), size=N_CLIENTES, replace=True, p=pesos_doc)

edad_hijo_mayor = np.full(N_CLIENTES, np.nan)
tiene_hijos = numero_hijos > 0
edad_hijo_mayor[tiene_hijos] = np.maximum(0, edad[tiene_hijos] - edades_parto[tiene_hijos])


# ─────────────────────────────────────────────────────────────────────────────
# ANTIGÜEDAD
# ─────────────────────────────────────────────────────────────────────────────
limite_biologico = edad - 18
antig_teorica    = np.floor(np.random.normal(10, 5, N_CLIENTES)).astype(int)
#Distribución Normal con Media de 10 años y desviación de 5 años
antiguedad_anos  = np.clip(antig_teorica, 0, limite_biologico)
# np.clip(array, min, max) → limita los valores entre min y max


# ─────────────────────────────────────────────────────────────────────────────
# TABLA CLIENTES 
# ─────────────────────────────────────────────────────────────────────────────
clientes = pd.DataFrame({
    'idCliente' :          id_clientes+1,
    'edad':                edad,
    'cp':                  cp,
    'latitud_hogar':       latitud_hogar,
    'longitud_hogar':      longitud_hogar,
    'tipo_empleo':         tipo_empleo,
    'nivel_estudios':      nivel_estudios,
    'usa_fintech':         usa_fintech,
    'hipoteca_imp_inicial': hipoteca_imp_inicial,
    'hipoteca_impagada':   hipoteca_impagada,
    'numero_hijos':        numero_hijos,
    'edad_hijo_mayor':     edad_hijo_mayor,
    'antiguedad_anos':     antiguedad_anos
})
clientes.to_csv(PATH_FICHEROS + 'clientes.txt', index=False, sep=';', decimal=',')
print('Datos clientes creados')


# =============================================================================
# PARTE 2. CREAR TRANSACCIONES
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# NÓMINAS Y PRESTACIONES
# ─────────────────────────────────────────────────────────────────────────────
idx_trabajan = np.where(np.isin(tipo_empleo, ['cuenta ajena', 'autonomo']))[0]
idx_paro_arr = np.where(tipo_empleo == 'parado')[0]

#NÓMINA:
# Número de trabajadores con nómina domiciliada (95% de los que trabajan):
n_nom = int(len(idx_trabajan) * 0.95) 

# Seleccionamos aleatoriamente los trabajadores que tienen la nómina domociliada 
# SIN reemplazamiento ya que cada trabajador puede salir como máximo una vez
idx_nom = np.random.choice(idx_trabajan, size=n_nom, replace=False)
imp_nom = np.tile(ingresos[idx_nom] / 12, 3) # np.tile(array, 3) → repite el array 3 veces (3 meses de nómina)
ids_nom = np.tile(idx_nom + 1, 3) # Repetimos los IDs 3 veces también (1 fila por mes)
T_Nominas = pd.DataFrame({'idCliente': ids_nom, 'importe': imp_nom, 'tipo': 'Ingreso'})

#PRESTACIONES:
#Número de parados con prestacion (80% de los parados):
n_pres = int(len(idx_paro_arr) * 0.80) 

# Seleccionamos aleatoriamente los parados que reciben prestacion
idx_pres = np.random.choice(idx_paro_arr, size=n_pres, replace=False)
imp_pres = np.tile((ingresos[idx_pres] / 12) * 0.70, 3)
# La prestación es el 70% del sueldo mensual, repetida 3 meses
ids_pres_arr = np.tile(idx_pres + 1, 3)
T_Prestaciones = pd.DataFrame({'idCliente': ids_pres_arr, 'importe': imp_pres, 'tipo': 'Ingreso'})

T_Ingresos = pd.concat([T_Nominas, T_Prestaciones], ignore_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# SEGUROS
# ─────────────────────────────────────────────────────────────────────────────
idx_seg_base = np.where(hipoteca_imp_inicial > 0)[0]
n_seg = int(len(idx_seg_base) * 0.25) # Solo el 25% paga el seguro este trimestre (se asume pago anual)
idx_seg = np.random.choice(idx_seg_base, size=n_seg, replace=False)

importe_seg = ingresos[idx_seg] * 0.1 # Base: 10% de los ingresos anuales
ruido_seg   = 0.9 + 0.2 * np.random.rand(len(idx_seg)) #Ruido: 0.9 + 0.2 * Uniforme[0,1) = Uniforme[0.9, 1.1)
importe_seg = importe_seg * ruido_seg

T_Seguros = pd.DataFrame({'idCliente': idx_seg + 1, 'importe': importe_seg, 'tipo': 'Seguro'})


# ─────────────────────────────────────────────────────────────────────────────
# ALIMENTACIÓN
# ─────────────────────────────────────────────────────────────────────────────
ids_base = np.arange(N_CLIENTES)   

#1ª Y 2ª Compra (TODOS): base + ruido proporcional al 10%.
imp_base = 40 + ingresos * 0.001
ruido1   = np.random.normal(0, 2, N_CLIENTES)
imp_ali1_2 = imp_base + 0.1 * ruido1 * imp_base

# 50% de los clientes tiene una 3ª compra. Seleccionamos sus índices:
idx2     = np.random.choice(N_CLIENTES, size=int(N_CLIENTES * 0.5), replace=False)
imp_base2 = 60 + ingresos[idx2] * 0.001
ruido2   = np.random.normal(0, 2, len(idx2))
imp_ali3  = imp_base2 + 0.1 * ruido2 * imp_base2

# 25% tiene una 4ª compra "capricho" con importe aleatorio.
idx3     = np.random.choice(idx2, size=int(N_CLIENTES * 0.25), replace=False)
imp_ali4  = np.random.uniform(8, 80, len(idx3)) # Importe entre 8€ y 80€ sin relación con los ingresos

ids_final_ali   = np.concatenate([ids_base, ids_base, idx2, idx3]) + 1
importes_ali    = np.abs(np.concatenate([imp_ali1_2, imp_ali1_2, imp_ali3, imp_ali4]))
T_Alimentacion  = pd.DataFrame({'idCliente': ids_final_ali, 'importe': importes_ali, 'tipo': 'Alimentacion'})


# ─────────────────────────────────────────────────────────────────────────────
# MODA
# ─────────────────────────────────────────────────────────────────────────────
# 50% de los clientes hace UNA compra de moda
list_ids_m = np.random.choice(N_CLIENTES, size=int(N_CLIENTES * 0.5), replace=False)
importe_m  = 70 + ingresos[list_ids_m] * 0.01
ruido_m    = np.random.normal(0, 1, len(list_ids_m))
importe_m  = importe_m + ruido_m * 0.1 * importe_m.mean()

# 25% tiene una 2ª compra con importe aleatorio entre 19€ y 200€
list_ids_m2 = np.random.choice(list_ids_m, size=int(N_CLIENTES * 0.25), replace=False)
importe_m2  = np.random.uniform(19, 200, len(list_ids_m2))

# 10% tiene una 3ª compra con distribución Normal centrada en 30€
list_ids_m3 = np.random.choice(list_ids_m2, size=int(N_CLIENTES * 0.1), replace=False)
importe_m3  = np.abs(np.random.normal(30, 20, len(list_ids_m3)))

ids_moda     = np.concatenate([list_ids_m, list_ids_m2, list_ids_m3]) + 1
importes_moda = np.abs(np.concatenate([importe_m, importe_m2, importe_m3]))
T_Moda = pd.DataFrame({'idCliente': ids_moda, 'importe': importes_moda, 'tipo': 'Moda'})


# ─────────────────────────────────────────────────────────────────────────────
# CENTRO DEPORTIVO
# ─────────────────────────────────────────────────────────────────────────────
# 1. Filtramos los clientes menores de 75 años
idx_menores_75 = np.where(edad < 75)[0]
n_dep = int(len(idx_menores_75) * 0.25)

# 2. Elegimos el 25% de forma aleatoria
idx_dep_elegidos = np.random.choice(idx_menores_75, size=n_dep, replace=False)

# 3. Inicializamos los importes base (solo para los elegidos)
ruido_dep = np.abs(np.random.normal(0, 3, len(idx_dep_elegidos)))
importe_dep = 20 + ruido_dep

# 4. Seleccionamos la mitad de ESOS elegidos para ser Premium
idx_premium_pos = np.random.choice(len(idx_dep_elegidos), size=len(idx_dep_elegidos) // 2, replace=False)
importe_dep[idx_premium_pos] += 30  # Sumamos la cuota premium (+30€)

# 5. Repetimos 3 veces (Trimestre) usando las variables corregidas
ids_cd     = np.tile(idx_dep_elegidos + 1, 3) # 🌟 CORREGIDO: idx_dep_elegidos en lugar de idx_dep
importes_cd = np.tile(importe_dep, 3)
T_CD = pd.DataFrame({'idCliente': ids_cd, 'importe': importes_cd, 'tipo': 'Centro_deportivo'})


# ─────────────────────────────────────────────────────────────────────────────
# RESTAURANTE
# ─────────────────────────────────────────────────────────────────────────────
# Iniciamos una lista vacía de Python para ir acumulando IDs de comensales
list_ids_r = []

# 60% de la población va al menos 1 vez al restaurante
ids_temp = np.random.choice(N_CLIENTES, size=int(N_CLIENTES * 0.6), replace=False)
list_ids_r.append(ids_temp) #los añadimos a la lista

# El 70% de los jóvenes van +2 veces más
idx_joven_r = np.where((edad > 20) & (edad < 30))[0]
n_joven_r   = int(len(idx_joven_r) * 0.7)
ids_temp2   = np.random.choice(idx_joven_r, size=n_joven_r, replace=False)
list_ids_r.extend([ids_temp2, ids_temp2])

# El 90% de las personas sin hijos van +2 veces más
idx_sin_hijos = np.where(numero_hijos == 0)[0]
n_sh = int(len(idx_sin_hijos) * 0.9)
ids_temp3 = np.random.choice(idx_sin_hijos, size=n_sh, replace=False)
list_ids_r.extend([ids_temp3, ids_temp3])

# El 90% de las personas con ingresos mensuales >4000 van +2 veces más
idx_renta_alta = np.where(ingresos / 12 > 4000)[0]
n_ra = int(len(idx_renta_alta) * 0.9)
ids_temp4 = np.random.choice(idx_renta_alta, size=n_ra, replace=False)
list_ids_r.extend([ids_temp4, ids_temp4])

# Unimos todos los sub-arrays acumulados en la lista 
list_ids_r = np.concatenate(list_ids_r)
importe_r  = 20 + 5 * (ingresos[list_ids_r] / 1000) + np.random.normal(0, 5, len(list_ids_r))
# Importe base 20€ + 5€ por cada 1000€ de ingresos anuales + ruido Normal
importe_r  = np.abs(importe_r)

T_Restaurante = pd.DataFrame({'idCliente': list_ids_r + 1, 'importe': importe_r, 'tipo': 'Restaurante'})


# ─────────────────────────────────────────────────────────────────────────────
# OCIO NOCTURNO Y FESTIVALES
# ─────────────────────────────────────────────────────────────────────────────
idx_joven_o  = np.where(edad < 35)[0]
idx_senior_o = np.where(edad >= 35)[0]

# Jóvenes: 70% son "fiesteros potenciales"; mayores: solo el 10%
idx_pot_j = np.random.choice(idx_joven_o,  size=int(len(idx_joven_o) * 0.70), replace=False)
idx_pot_s = np.random.choice(idx_senior_o, size=int(len(idx_senior_o) * 0.10), replace=False)
idx_potencial = np.concatenate([idx_pot_j, idx_pot_s])

#Cada persona del grupo anterior recibe un número aleatorio entre 0 y 8 (representa cuántas veces ha salido de fiesta) 
frecuencia = np.random.randint(0, 9, size=len(idx_potencial))

mask_activos = frecuencia > 0 # filtramos los que salen al menos 1 vez
idx_activos  = idx_potencial[mask_activos]
freq_activos = frecuencia[mask_activos]

# Un base_gasto por persona 
base_gasto = 15 + np.random.rand(len(idx_activos)) * 45

# Expandimos: cada cliente se repite tantas veces como su frecuencia
ids_ocio_arr  = np.repeat(idx_activos, freq_activos)
base_expandida = np.repeat(base_gasto, freq_activos)

# Ruido sobre todas las transacciones a la vez
imps_ocio_arr = base_expandida + np.random.randn(len(ids_ocio_arr)) * 5

# Festivales: 10% de los fiesteros van a UN festival (100€-350€)
n_fest   = int(len(idx_potencial) * 0.10)
idx_fest = np.random.choice(len(idx_potencial), size=n_fest, replace=False)
ids_fest_arr  = idx_potencial[idx_fest]
imps_fest_arr = 100 + np.random.rand(n_fest) * 250

ids_final_ocio  = np.concatenate([ids_ocio_arr, ids_fest_arr])
imps_final_ocio = np.abs(np.concatenate([imps_ocio_arr, imps_fest_arr]))
T_Ocio = pd.DataFrame({'idCliente': ids_final_ocio+1, 'importe': imps_final_ocio, 'tipo': 'Ocio Nocturno'})


# ─────────────────────────────────────────────────────────────────────────────
# TRANSFERENCIAS INTERNACIONALES (REMESAS)
# ─────────────────────────────────────────────────────────────────────────────
# 15% de la población envía remesas al exterior
n_emisores  = int(N_CLIENTES * 0.15)
ids_emisores = np.random.choice(N_CLIENTES, size=n_emisores, replace=False)   

# Repetimos 3 veces (una transferencia por mes durante el trimestre):
list_ids_rem = np.tile(ids_emisores, 3)
# Importe base: 150€ + 5% de los ingresos anuales+ Ruido Normal:
importe_base_rem = 150 + ingresos[ids_emisores] * 0.05
ruido_rem  = np.random.normal(0, 30, len(list_ids_rem))
importe_rem = np.tile(importe_base_rem, 3) + ruido_rem
importe_rem = np.maximum(importe_rem, 50) # Mínimo 50€ por transferencia

n_remesas = np.zeros(N_CLIENTES, dtype=int)
n_remesas[ids_emisores] = 3
# Guardamos el conteo de remesas por cliente

T_Remesas = pd.DataFrame({
    'idCliente': list_ids_rem + 1,
    'importe':   importe_rem,
    'tipo':      'Transferencia Internacional'
})


# ─────────────────────────────────────────────────────────────────────────────
# AMAZON
# ─────────────────────────────────────────────────────────────────────────────
idx_target = np.where((edad >= 35) & (edad <= 44))[0]
idx_resto  = np.where((edad < 35) | (edad > 44))[0]

# 65% del target y 40% del resto compraron en Amazon este trimestre:
ids_compradores = np.concatenate([
    np.random.choice(idx_target, size=int(len(idx_target) * 0.65), replace=False),
    np.random.choice(idx_resto,  size=int(len(idx_resto)  * 0.40), replace=False),
])

num_pedidos = np.random.poisson(2.75, size=len(ids_compradores))
#distribución de Poisson con Lambda=2.75 → media de 2.75 pedidos por trimestre
ids_amazon  = np.repeat(ids_compradores, num_pedidos) 

# Ticket medio ~31.5€ con variación Normal(0,15):
importes_amazon = 31.5 + np.random.normal(0, 15, len(ids_amazon))
idx_promo = np.random.rand(len(importes_amazon)) < 0.40 # 40% de las compras están en promoción
importes_amazon[idx_promo] *= 0.85 # Las compras en promo tienen un 15% de descuento
# Evitamos importes < 5€: los sustituimos por valores entre 5€ y 10€
precio_bajo = importes_amazon < 5
importes_amazon[precio_bajo] = 5 + np.random.rand(precio_bajo.sum()) * 5

T_Amazon = pd.DataFrame({
    'idCliente': ids_amazon + 1,
    'importe':   np.abs(importes_amazon),
    'tipo':      'Amazon'
})


# ─────────────────────────────────────────────────────────────────────────────
# SUSCRIPCIONES DIGITALES
# ─────────────────────────────────────────────────────────────────────────────
# 60% de los clientes tiene alguna suscripción (Netflix, Spotify...)
idx_suscrip = np.random.choice(N_CLIENTES, size=int(N_CLIENTES * 0.60), replace=False)
# Media ~17€ (12 base + Normal(5,2))
importe_s   = 12 + np.random.normal(5, 2, len(idx_suscrip))

# Repetimos 3 veces para cubrir el trimestre
idx_sus     = np.tile(idx_suscrip, 3)
importe_sus = np.tile(importe_s, 3)

T_Suscripciones = pd.DataFrame({
    'idCliente': idx_sus + 1,
    'importe':   np.abs(importe_sus),
    'tipo':      'Suscripcion'
})


# ─────────────────────────────────────────────────────────────────────────────
# GAMING
# ─────────────────────────────────────────────────────────────────────────────
# Solo jóvenes de 18 a 29 años
idx_jovenes_g = np.where((edad >= 18) & (edad <= 29))[0]
# 62.5% de los jóvenes compra videojuegos
n_comp_joven  = int(len(idx_jovenes_g) * 0.625)
ids_gamers    = np.random.choice(idx_jovenes_g, size=n_comp_joven, replace=False)

# Entre 1 y 2 compras por trimestre
num_pedidos_g = np.random.randint(1, 3, size=len(ids_gamers))
ids_gamer_final = np.repeat(ids_gamers, num_pedidos_g)

importes_gamer = 10 + np.random.exponential(25, size=len(ids_gamer_final))
# Distribución Exponencial porque la mayoría gasta poco pero algunos gastan mucho
importes_gamer = np.minimum(importes_gamer, 70) # Techo de 70€ 

# 30.4% de los jóvenes también paga suscripciones de gaming (PS Plus, Game Pass...)
idx_susc_g = np.random.choice(idx_jovenes_g, size=int(len(idx_jovenes_g) * 0.304), replace=False)
precios_posibles = [7.99, 11.99, 14.99]
precios_aleatorios = np.random.choice(precios_posibles, size=len(idx_susc_g))

ids_gamer_final  = np.concatenate([ids_gamer_final, idx_susc_g])
importes_gamer   = np.concatenate([importes_gamer, precios_aleatorios])

T_Gaming = pd.DataFrame({
    'idCliente': ids_gamer_final + 1,
    'importe':   np.abs(importes_gamer),
    'tipo':      'Gaming'
})


# ─────────────────────────────────────────────────────────────────────────────
# INVERSIÓN
# ─────────────────────────────────────────────────────────────────────────────
# Probabilidad de invertir: base 23% + hasta 10% adicional según ingresos
prob_invertir  = 0.23 + (ingresos / ingresos.max()) * 0.10
idx_inversores = np.where(np.random.rand(N_CLIENTES) < prob_invertir)[0]

# Invertir entre el 5% y el 15% de los ingresos anuales:
pct_inversion    = 0.05 + 0.10 * np.random.rand(len(idx_inversores))
importes_inversion = ingresos[idx_inversores] * pct_inversion

T_Inversion = pd.DataFrame({
    'idCliente': idx_inversores + 1,
    'importe':   np.abs(importes_inversion),
    'tipo':      'Inversion'
})


# =============================================================================
# PARTE 3. CREAR TABLA TRANSACCIONES
# =============================================================================

T_Total = pd.concat([
    T_Ingresos,
    T_Seguros,
    T_Alimentacion,
    T_Restaurante,
    T_CD,
    T_Moda,
    T_Amazon,
    T_Gaming,
    T_Suscripciones,
    T_Inversion,
    T_Ocio,
    T_Remesas,
], ignore_index=True)

n_trans = len(T_Total)



# ── Fecha de la transacción (Q1 2026: 01/01/2026 – 31/03/2026) ───────────────
# El trimestre tiene 90 días (enero=31, febrero=28, marzo=31).
# Pesos diarios con estacionalidad realista:
#   - Enero: arranque lento (vuelta de Navidad, cuesta de enero)
#   - Febrero: recuperación gradual, pico en San Valentín (día 14)
#   - Marzo: repunte claro (más actividad comercial pre-primavera)
 
dias_q1 = 90  # 31 ene + 28 feb + 31 mar
 
# Curva base con tendencia creciente a lo largo del trimestre
tendencia = np.linspace(0.7, 1.3, dias_q1)
 
# Pico San Valentín (día 45 = 14 feb): +40% ese día y ±1 día
pico_sv = np.zeros(dias_q1)
for d in [43, 44, 45]:          # 12, 13 y 14 de febrero
    pico_sv[d] = 0.40 if d == 44 else 0.20
 
# Bajón fin de enero (días 25-31): -15% (cuesta de enero)
cuesta = np.zeros(dias_q1)
cuesta[24:31] = -0.15
 
pesos_diarios = tendencia + pico_sv + cuesta
pesos_diarios = np.maximum(pesos_diarios, 0.1)   # nunca negativo
pesos_diarios = pesos_diarios / pesos_diarios.sum()
 
# Asignamos un día del trimestre a cada transacción
dia_offset = np.random.choice(dias_q1, size=n_trans, replace=True, p=pesos_diarios)
 
fecha_inicio = pd.Timestamp('2026-01-01')
fechas = fecha_inicio + pd.to_timedelta(dia_offset, unit='D')
T_Total['fecha'] = fechas.strftime('%Y-%m-%d')
 
T_Total.to_csv(PATH_FICHEROS + 'transacciones.txt', index=False, sep=';', decimal=',')
print('Datos transacciones creados')

# =============================================================================
# PARTE 4. CREAR PROBLEMA - STABLE COINS
# =============================================================================

RATIO_ADOPTAN_PASADO = 0.15 # 15% ya usa stablecoins
RATIO_ADOPTAN_FUTURO = RATIO_ADOPTAN_PASADO + 0.20  # 35% adicional adoptará en el futuro
RATIO_INVERSION_SC   = 0.08 # Invierten el 8% anual de sus ingresos en SC


# ── 4.1 Gasto mensual en Stable Coins (PASADO) ───────────────────────────────
gasto_SC_pasado = RATIO_INVERSION_SC * (1 / 12) * ingresos
gasto_SC_pasado += np.random.uniform(0, 50, N_CLIENTES)
# Gasto mensual base en SC: 8% anual de los ingresos / 12 meses + ruido Uniforme[0, 50€]

# Techos progresivos
gasto_1500 = gasto_SC_pasado > 1500
gasto_1000 = (gasto_SC_pasado > 1000) & ~gasto_1500
gasto_600  = (gasto_SC_pasado > 600)  & ~gasto_1500 & ~gasto_1000

# Por encima del techo, el gasto sigue creciendo pero más despacio (compresión)
gasto_SC_pasado[gasto_1500] = 1500 + (gasto_SC_pasado[gasto_1500] - 1500) * 0.80
gasto_SC_pasado[gasto_1000] = 1000 + (gasto_SC_pasado[gasto_1000] - 1000) * 0.75
gasto_SC_pasado[gasto_600]  = 600  + (gasto_SC_pasado[gasto_600]  - 600)  * 0.70

# Los que tienen hipoteca impagada no invierten en SC (problemas de liquidez)
idx_impago = hipoteca_impagada == 1
gasto_SC_pasado[idx_impago] = 0


# ── 4.2 Gasto mensual en Stable Coins (FUTURO) ───────────────────────────────
# El gasto futuro crece entre un 5% y un 20% respecto al pasado
gasto_SC_futuro = gasto_SC_pasado * (1 + np.random.uniform(0.05, 0.20, N_CLIENTES))

# Los que envían remesas al exterior tienen un incentivo extra de 200€/mes
gasto_SC_futuro[ids_emisores] += 200

# Los impagadores siguen sin poder invertir en el futuro
gasto_SC_futuro[idx_impago] = 0


# ── 4.3 Probabilidad de adoptar Stable Coins ─────────────────────────────────
# Probabilidad base de adopción: entre 5% y 20% para todos
prob_SC = np.random.uniform(0.05, 0.20, N_CLIENTES)

# Los jóvenes son más propensos a adoptar tecnologías financieras nuevas
prob_SC[edad < 35] += 0.15

# Ya usan otras fintechs → perfil abierto a innovación financiera
prob_SC[usa_fintech == 1] += 0.10

# Ya invierten → perfil inversor activo, más probable que adopten SC
prob_SC[idx_inversores]   += 0.20

# Mayor nivel educativo → mejor comprensión del producto
mask_estudios_sup = np.isin(nivel_estudios, ['Grado', 'Postgrado'])
prob_SC[mask_estudios_sup] += 0.15

# Los gamers están familiarizados con economías digitales y tokens
gamers_uniq = np.unique(ids_gamer_final) # np.unique() elimina duplicados (necesitamos los IDs únicos)
prob_SC[gamers_uniq] += 0.10


# ── 4.3b Concentración geográfica de adoptantes iniciales ────────────────────
# Definimos 8 clusters (zonas "early adopter"): barrios concretos de ciudades reales.
# Estos son los focos donde ya circula la cultura cripto/fintech.
CLUSTERS_GEO = [
    # (lat,    lon,    radio_km, boost)       # Descripción
    # NOTA: radio_km ampliado para que los clusters sean detectables
    # en un mapa de España en Power BI. El boost alto asegura
    # contraste claro entre zonas adoptantes y no adoptantes.
    (40.4168, -3.7038,  8.0,   0.55),   # Madrid centro (Malasaña/Chueca)
    (40.4530, -3.6883,  6.0,   0.50),   # Madrid norte  (Hortaleza/tech hub)
    (41.3851,  2.1734,  8.0,   0.55),   # Barcelona (Poblenou/22@ distrito tech)
    (41.4036,  2.1744,  5.0,   0.45),   # Barcelona (Gràcia)
    (37.3886, -5.9823,  6.0,   0.45),   # Sevilla (Triana/centro)
    (43.2630, -2.9350,  6.0,   0.40),   # Bilbao (Abando)
    (39.4699, -0.3763,  6.0,   0.40),   # Valencia (Ruzafa)
    (37.1773, -3.5986,  5.0,   0.35),   # Granada (centro universitario)
]

KM_POR_GRADO_CLUSTER = 111.0

for lat_c, lon_c, radio_km, boost in CLUSTERS_GEO:
    dlat = latitud_hogar  - lat_c
    dlon = (longitud_hogar - lon_c) * np.cos(np.radians(lat_c))
    dist_km = np.sqrt(dlat**2 + dlon**2) * KM_POR_GRADO_CLUSTER
    
    # Función Gaussiana: influencia máxima en el centro, cae con la distancia
    sigma_cluster = radio_km / 2.0   # a "radio_km" la influencia es ~13%
    peso_geo = np.exp(-(dist_km**2) / (2 * sigma_cluster**2))
    
    # Sumamos el boost geográfico a la probabilidad existente
    prob_SC += boost * peso_geo

prob_SC = np.minimum(prob_SC, 1.0)


# ── 4.4 Asignación de adopción ────────────────────────────────────────────────
# Decides quién usará Stablecoins y quien ya la usa
n_adoptan_pasado = round(N_CLIENTES * RATIO_ADOPTAN_PASADO)
# Del total restante (los que no adoptaron en el pasado), el 35% adoptará:
n_adoptan_futuro = round((N_CLIENTES - n_adoptan_pasado) * RATIO_ADOPTAN_FUTURO)

orden       = np.argsort(prob_SC)[::-1]
ids_orden   = id_clientes[orden]  #Cogemos la lista de probabilidades y la ordenamos de mayor a menor. Así, 
# elegimps a los N más probables 

# Los adoptantes iniciales (pasado) son el TOP absoluto de probabilidad (Tus clusters)
SC_inicial_ids = ids_orden[:n_adoptan_pasado]

# Los adoptantes futuros son los siguientes en la lista de probabilidad
SC_futuro_ids  = ids_orden[n_adoptan_pasado : n_adoptan_pasado + n_adoptan_futuro]

# A los futuros sí puedes darles un toque aleatorio si quieres, y les sumas las remesas
SC_futuro_ids = np.unique(np.concatenate([SC_futuro_ids, ids_emisores])) 


# ── 4.5 Construcción adopción inicial ────────────────────────────────────────
gasto_visible    = np.zeros(N_CLIENTES)
adoptado_inicial = np.zeros(N_CLIENTES, dtype=int)
# Inicializamos todo a 0: por defecto nadie ha adoptado ni gasta nada

gasto_visible[SC_inicial_ids]    = gasto_SC_pasado[SC_inicial_ids]
adoptado_inicial[SC_inicial_ids] = 1
# Solo los adoptantes iniciales tienen gasto visible > 0 y adoptado = 1


# ── 4.6 Incentivo geolocalizado (efecto vecindario) ──────────────────────────
#clientes que ya adoptaron en el pasado (SC_inicial_ids)
lat_SC = latitud_hogar[SC_inicial_ids]
lon_SC = longitud_hogar[SC_inicial_ids]

# Ahora definimos los parámetros directamente EN KILÓMETROS REALES
SIGMA_KM = 3.0   # desviación estándar de la campana de Gauss (Define la velocidad a la que se pierde la influencia)
# Ampliado de 0.5 km a 3.0 km para que el efecto vecindario sea visible en Power BI.
# Con sigma=3 km, la influencia a 6 km (2 sigmas) cae al 13%, formando manchas
# de densidad claramente detectables en un mapa de España.

exposicion = np.zeros(N_CLIENTES) #Acumularemos el "nivel de contagio cripto" que recibe cada ciudadano de su entorno.
KM_POR_GRADO = 111.0  # Factor de conversión aproximado para España (un grado de latitud equivale aproximadamente a 111 kilómetros)
BLOQUE = 1000 #Si intentaras calcular la distancia de todos los clientes contra todos los adoptantes a la vez, seria eterno
for start in range(0, N_CLIENTES, BLOQUE):
    end      = min(start + BLOQUE, N_CLIENTES)
    dlat     = latitud_hogar[start:end, None] - lat_SC[None, :]
    dlon     = longitud_hogar[start:end, None] - lon_SC[None, :]
    lat_med  = latitud_hogar[start:end, None]

    # 1. Calculamos la distancia en grados (con corrección de longitud)
    #d^2 = dlat^2 + dlon^2 => Si dejamos la fórmula tal cual, se asume que los "grados" de latitud valen lo mismo que los de longitud.
    dist2_grados = dlat**2 + (dlon * np.cos(np.radians(lat_med)))**2

    # 2. Pasamos la distancia a kilómetros cuadrados
    dist2_km = dist2_grados * (KM_POR_GRADO**2)

    # 3. La exponencial ahora trabaja con kilómetros reales perfectos
    #Usamos una función Gaussiana No Normalizada (Kernel RBF).
    # Omitimos el factor estadístico "1 / (sigma * sqrt(2*pi))" por dos razones de negocio:
    # 1. No buscamos una Densidad de Probabilidad (donde el área total bajo la curva sume 1).
    # 2. Buscamos que la influencia de un vecino a distancia cero sea Máxima e igual a 1 (100%),
    # y que el efecto de múltiples vecinos sea acumulativo (suma de intensidades).
    exposicion[start:end] = np.exp(-dist2_km / (2 * SIGMA_KM**2)).sum(axis=1)

techo   = np.percentile(exposicion[exposicion > 0], 99) #De los que tienen exposición, calcula el percentil 99.

# Se divide la exposición entre el techo calculado (percentil 99) para normalizar la variable.
# A aquellos individuos que se encuentran por encima de dicho umbral, se les asigna un valor máximo de uno.
# Para que, a partir de cierto nivel de saturación de vecinos, el efecto de contagio social ya sea máximo 
exposicion_norm = np.clip(exposicion / techo, 0, 1)

# Incentivo gradual: +0% si nadie cerca, hasta +40% si zona muy densa, haciendo que el impacto sea totalmente gradual 
# y realista para cada uno de los 300.000 clientes.
factor = 1 + exposicion_norm * 0.40
factor[hipoteca_impagada == 1] = 1.0   # impagadores no reciben incentivo
gasto_SC_futuro *= factor
gasto_SC_futuro  = np.minimum(gasto_SC_futuro, 1500)


# ── 4.7 Tablas de salida ──────────────────────────────────────────────────────
gasto_SC_pasado = gasto_SC_pasado.round(1)
gasto_SC_futuro = gasto_SC_futuro.round(1)

stablecoins = pd.DataFrame({
    'id':        id_clientes+1,
    'adoptado':  adoptado_inicial,
    'gasto_SC':  gasto_visible,
})
stablecoins.to_csv(PATH_FICHEROS + 'stablecoins.txt', index=False, sep=';', decimal=',')

adoptado_final = np.zeros(N_CLIENTES, dtype=int)
adoptado_final[SC_inicial_ids] = 1
adoptado_final[SC_futuro_ids]  = 1

stablecoins_oculta = pd.DataFrame({
    'id':              id_clientes+1,
    'adoptado_pasado': adoptado_inicial,
    'adoptado_futuro': adoptado_final,
    'gasto_pasado':    gasto_SC_pasado,
    'gasto_futuro':    gasto_SC_futuro,
})
stablecoins_oculta.to_csv(PATH_FICHEROS + 'stablecoinsOculta.txt', index=False, sep=';', decimal=',')

print('StableCoins generadas correctamente')