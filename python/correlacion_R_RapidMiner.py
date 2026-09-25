import pandas as pd

# Paso 1: cargar los dos ficheros de scoring
rm = pd.read_csv("resultado_scoring_stablecoin.csv", sep=";")
r  = pd.read_csv("resultadosR.csv", sep=";", decimal=",")   # ojo: R usa coma decimal

# Paso 2: cruzar por idCliente, para tener en la misma fila el dato de cada cliente
# segun las dos herramientas (con sufijos _rm y _r para distinguir las columnas repetidas)
comparacion = rm.merge(r, on="idCliente", suffixes=("_rm", "_r"))

# Paso 3: .corr() calcula el coeficiente de correlacion de Pearson entre dos columnas
# (va de -1 a 1; cerca de 1 significa que ambas herramientas predicen prácticamente lo mismo)
correlacion_prediccion = comparacion["prediction(gasto_SC)"].corr(comparacion["prediction_gasto_SC"])
correlacion_distancia  = comparacion["distancia_centroide_rm"].corr(comparacion["distancia_centroide_r"])

print("Correlacion prediccion gasto:", correlacion_prediccion)
print("Correlacion distancia centroide:", correlacion_distancia)