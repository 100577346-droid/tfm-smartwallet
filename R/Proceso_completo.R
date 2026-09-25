## ============================================================
## 03_proceso_completo.R
## Equivalente en R del proceso construido en RapidMiner
## (rama de clustering K-Means + rama de regresion Random Forest)
## ============================================================

library(randomForest)

## ------------------------------------------------------------
## 0. HIPERPARAMETROS Y RUTAS
## ------------------------------------------------------------

SEMILLA         <- 1992   
K_CLUSTERS      <- 8      # numero de clusteres seleccionado 
NSTART_KMEANS   <- 25     # reinicios de kmeans
N_ARBOLES       <- 300    # numero de arboles del Random Forest
SUBSET_RATIO    <- 0.296  # proporcion de atributos candidatos por division (~p/3)
HOJA_MINIMA     <- 5      # minimal_leaf_size en RapidMiner -> nodesize en R

RUTA_ENTRADA <- "D:/Master/TFM/DATOS/union_dataset.csv"
RUTA_SALIDA  <- "D:/Master/TFM/R/resultadosR.csv"


## ------------------------------------------------------------
## 1. PREPARACION COMUN DE LOS DATOS
##    (equivalente a: Read CSV -> Set Role idCliente ->
##     Select Attributes Perfil -> Nominal to Numerical -> Multiply Ramas)
## ------------------------------------------------------------

datos <- read.csv2(RUTA_ENTRADA, sep = ";", dec = ",",
                   stringsAsFactors = FALSE, encoding = "latin1")

# Selección de atributos
variables_perfil <- c(
  "idCliente", "adoptado", "antiguedad_anos", "edad",
  "gasto_Alimentacion", "gasto_Amazon", "gasto_Centro_deportivo",
  "gasto_Gaming", "gasto_Inversion", "gasto_Moda", "gasto_Ocio_Nocturno",
  "gasto_Restaurante", "gasto_SC", "gasto_Seguro", "gasto_Suscripcion",
  "gasto_Transferencia_Internacional", "latitud_hogar", "longitud_hogar",
  "nivel_estudios", "numero_hijos", "suma_ingresos", "tiene_hijos",
  "usa_fintech", "hipoteca_impagada", "num_movimientos_gasto",
  "hipoteca_imp_inicial", "edad_hijo_mayor", "tiene_ingresos_declarados"
)
datos <- datos[, variables_perfil]

# edad_hijo_mayor es NaN cuando el cliente no tiene hijos.
# A diferencia de RapidMiner -cuyos operadores de arbol gestionan los 
# valores ausentes de forma nativa-, randomForest() en R falla si recibe NA,
# por lo que aqui se imputan explicitamente a 0.
datos$edad_hijo_mayor[is.na(datos$edad_hijo_mayor)] <- 0

# Nominal to Numerical (dummy coding, categoria de referencia = la mas
# frecuente / la de interes, igual que en RapidMiner):
#   nivel_estudios             -> referencia "Grado"
#   usa_fintech                -> referencia "0"
#   hipoteca_impagada          -> referencia "0"
#   tiene_hijos                -> referencia "0"
#   tiene_ingresos_declarados  -> referencia "0"
datos$nivel_estudios_Postgrado   <- as.integer(datos$nivel_estudios == "Postgrado")
datos$nivel_estudios_Primarios   <- as.integer(datos$nivel_estudios == "Primarios")
datos$nivel_estudios_Secundarios <- as.integer(datos$nivel_estudios == "Secundarios")
datos$usa_fintech_1               <- as.integer(datos$usa_fintech == 1)
datos$hipoteca_impagada_1         <- as.integer(datos$hipoteca_impagada == 1)
datos$tiene_hijos_1               <- as.integer(datos$tiene_hijos == 1)
datos$tiene_ingresos_declarados_1 <- as.integer(datos$tiene_ingresos_declarados == 1)

# las columnas nominales originales ya no se necesitan (RapidMiner las
# sustituye por sus dummies al codificar)
datos$nivel_estudios             <- NULL
datos$usa_fintech                <- NULL
datos$hipoteca_impagada          <- NULL
datos$tiene_hijos                <- NULL
datos$tiene_ingresos_declarados  <- NULL

# Multiply Ramas: se trabaja sobre dos copias independientes del dataset,
# una para cada rama del modelo
rama_clustering <- datos
rama_regresion  <- datos


## ------------------------------------------------------------
## 2. RAMA DE CLUSTERING (K-MEANS)
## ------------------------------------------------------------

# Las doce variables finales del clustering (Select Attributes Clustering Vars)
vars_clustering <- c(
  "edad", "latitud_hogar", "longitud_hogar",
  "usa_fintech_1", "hipoteca_impagada_1",
  "nivel_estudios_Postgrado", "nivel_estudios_Primarios", "nivel_estudios_Secundarios",
  "num_movimientos_gasto", "gasto_Inversion",
  "gasto_Transferencia_Internacional", "gasto_total_resto"
)

# Cadena de preprocesamiento compartida por adoptantes y no adoptantes
# (Generate gasto_total_resto -> Aplicar log1p -> Select Attributes Clustering
# Vars). Se define como funcion, en lugar de duplicar el codigo en cada
# rama, para dejar explicito que ambos subconjuntos reciben exactamente
# el mismo tratamiento antes de estandarizar.
log1p_seguro <- function(x) log1p(pmax(x, 0))

preparar_variables_clustering <- function(df) {
  df$gasto_total_resto <- with(df,
                               gasto_Alimentacion + gasto_Amazon + gasto_Centro_deportivo + gasto_Gaming +
                                 gasto_Moda + gasto_Ocio_Nocturno + gasto_Restaurante + gasto_Seguro +
                                 gasto_Suscripcion
  )
  df$num_movimientos_gasto <- log1p_seguro(df$num_movimientos_gasto)
  df$gasto_Inversion       <- log1p_seguro(df$gasto_Inversion)
  df$gasto_Transferencia_Internacional <- log1p_seguro(df$gasto_Transferencia_Internacional)
  df$gasto_total_resto     <- log1p_seguro(df$gasto_total_resto)
  df[, vars_clustering]
}

## --- Paso 1: entrenamiento del modelo sobre los adoptantes -----------

adoptantes_cl <- rama_clustering[rama_clustering$adoptado == 1, ]
X_adoptantes  <- preparar_variables_clustering(adoptantes_cl)

# Normalize (Z-transformation), guardando centro y escala para poder
# aplicar exactamente la misma transformacion sobre los no adoptantes
# (equivalente al "preprocessing model" de RapidMiner)
X_adoptantes_z <- scale(X_adoptantes)
centro_z <- attr(X_adoptantes_z, "scaled:center")
escala_z <- attr(X_adoptantes_z, "scaled:scale")

# Clustering K-Means: k = 8, 25 reinicios, semilla local fija
set.seed(SEMILLA)
modelo_kmeans <- kmeans(X_adoptantes_z, centers = K_CLUSTERS,
                        nstart = NSTART_KMEANS, iter.max = 100)

# Aggregate Centroides: valor medio de cada variable por cluster.
matriz_centroides <- modelo_kmeans$centers  # matriz k_clusters x 12, ya en escala Z


## --- Paso 2: puntuacion de los no adoptantes --------------------------

no_adoptantes_cl <- rama_clustering[rama_clustering$adoptado == 0, ]
X_no_adoptantes  <- preparar_variables_clustering(no_adoptantes_cl)

# Apply Model Normalize: se aplica el MISMO centro/escala aprendidos
# sobre los adoptantes (no se reajusta un modelo nuevo)
X_no_adoptantes_z <- scale(X_no_adoptantes, center = centro_z, scale = escala_z)

# Apply Model Cluster: se calcula manualmente la distancia euclidea de
# cada no adoptante a los ocho centroides y se asigna el mas cercano.
matriz_distancias <- matrix(NA_real_, nrow = nrow(X_no_adoptantes_z), ncol = K_CLUSTERS)
for (k in seq_len(K_CLUSTERS)) {
  diferencias <- sweep(X_no_adoptantes_z, 2, matriz_centroides[k, ], FUN = "-")
  matriz_distancias[, k] <- sqrt(rowSums(diferencias^2))
}

# cluster: indice del centroide mas cercano, en base 0 para replicar la
# numeracion 0..7 que usa RapidMiner
no_adoptantes_cl$cluster             <- apply(matriz_distancias, 1, which.min) - 1
no_adoptantes_cl$distancia_centroide <- apply(matriz_distancias, 1, min)

salida_clustering <- no_adoptantes_cl[, c("idCliente", "cluster", "distancia_centroide")]


## ------------------------------------------------------------
## 3. RAMA DE REGRESION (RANDOM FOREST)
## ------------------------------------------------------------

## --- Paso 1: entrenamiento y validacion mediante error OOB -------------

adoptantes_rg <- rama_regresion[rama_regresion$adoptado == 1, ]
adoptantes_rg$adoptado  <- NULL   # Select Attributes: excluye "adoptado"
adoptantes_rg$idCliente <- NULL   # idCliente no interviene como predictor

p_predictores  <- ncol(adoptantes_rg) - 1  # todas las columnas menos gasto_SC
mtry_regresion <- max(1, round(SUBSET_RATIO * p_predictores))

set.seed(SEMILLA)
modelo_rf <- randomForest(
  gasto_SC ~ .,
  data       = adoptantes_rg,
  ntree      = N_ARBOLES,
  mtry       = mtry_regresion,
  nodesize   = HOJA_MINIMA,
  importance = TRUE
)
# Muestra / Media del gasto SC en adoptantes
gasto_medio_adoptantes <- mean(adoptantes_rg$gasto_SC)

# Impresión por pantalla para comprobación rápida
cat(sprintf("Gasto medio SC (Adoptantes): %.2f\n", gasto_medio_adoptantes))

# Metricas OOB tras los N_ARBOLES arboles
rmse_oob <- sqrt(tail(modelo_rf$mse, 1))
r2_oob   <- tail(modelo_rf$rsq, 1)

# Error relativo medio sobre las predicciones OOB
# (se excluyen los clientes con gasto real ~0, tipicamente por
# hipoteca impagada, ya que el error relativo no esta definido
# de forma significativa cuando el valor real es practicamente nulo)
casos_validos <- adoptantes_rg$gasto_SC > 1

error_relativo_medio <- mean(
  abs(adoptantes_rg$gasto_SC[casos_validos] - modelo_rf$predicted[casos_validos]) /
    adoptantes_rg$gasto_SC[casos_validos]
)

cat(sprintf("Clientes excluidos del calculo (gasto casi nulo): %d de %d\n",
            sum(!casos_validos), length(casos_validos)))

cat(sprintf("RMSE (OOB, %d arboles): %.3f\n", N_ARBOLES, rmse_oob))
cat(sprintf("R2 (OOB): %.3f\n", r2_oob))
cat(sprintf("Error relativo medio (OOB): %.3f%%\n", 100 * error_relativo_medio))

# Importancia de variables
importancia <- importance(modelo_rf)
importancia_ordenada <- importancia[order(-importancia[, "%IncMSE"]), ]
cat("\nVariables mas importantes (top 10, por %IncMSE):\n")
print(round(head(importancia_ordenada, 10), 2))


## --- Paso 2: estimacion sobre los no adoptantes ------------------------

no_adoptantes_rg <- rama_regresion[rama_regresion$adoptado == 0, ]
id_no_adoptantes_rg <- no_adoptantes_rg$idCliente

no_adoptantes_rg$adoptado  <- NULL
no_adoptantes_rg$idCliente <- NULL
no_adoptantes_rg$gasto_SC  <- NULL  # variable objetivo, no se conoce aqui

prediccion_gasto <- predict(modelo_rf, newdata = no_adoptantes_rg)

salida_regresion <- data.frame(
  idCliente = id_no_adoptantes_rg,
  prediction_gasto_SC = prediccion_gasto
)


## ------------------------------------------------------------
## 4. COMBINACION FINAL Y EXPORTACION
##    (equivalente a: Join Final por idCliente -> Write CSV Resultado)
## ------------------------------------------------------------

resultado_final <- merge(salida_clustering, salida_regresion,
                         by = "idCliente", all = FALSE)  # inner join

# 1. Exportar dataset scoring no adoptantes (Resultados del scoring)
write.table(resultado_final, RUTA_SALIDA, sep = ";", dec = ",",
            row.names = FALSE, quote = FALSE, fileEncoding = "UTF-8")

cat(sprintf("\nProceso completo. %d clientes no adoptantes puntuados.\n",
            nrow(resultado_final)))
cat(sprintf("Resultado guardado en: %s\n", RUTA_SALIDA))

# 2. Exportar métricas de rendimiento a CSV
metricas <- data.frame(
  RMSE                   = rmse_oob,
  R2                     = r2_oob,
  Error_Relativo_Pct     = 100 * error_relativo_medio,
  Gasto_Medio_Adoptantes = gasto_medio_adoptantes
)
write.csv2(metricas, "D:/Master/TFM/R/metricas_rendimiento.csv", row.names = FALSE)

# Exportar pares predicho/real (OOB) para el gráfico de diagnóstico
validacion_regresion <- data.frame(
  gasto_real          = adoptantes_rg$gasto_SC,
  gasto_predicho_oob  = modelo_rf$predicted
)
write.csv2(validacion_regresion, "D:/Master/TFM/R/prediccion_vs_real.csv", row.names = FALSE)

# 3. Exportar la tabla completa de importancia de variables a CSV
tabla_importancia <- as.data.frame(importance(modelo_rf))
write.csv2(tabla_importancia, "D:/Master/TFM/R/importancia_variables.csv", row.names = TRUE)

# Grafico de diagnostico: predicho (OOB) vs. real
png("D:/Master/TFM/R/predicho_vs_real.png", width = 1400, height = 1400, res = 200)

real <- validacion_regresion$gasto_real
pred <- validacion_regresion$gasto_predicho_oob
lims <- range(c(real, pred))

par(pty = "s")
plot(real, pred,
     pch = 16, cex = 0.4, col = rgb(0.1, 0.3, 0.7, 0.06),
     xlim = lims, ylim = lims,
     xlab = "Gasto real en stablecoins (€)",
     ylab = "Gasto predicho (OOB) (€)",
     main = "Predicho vs. real — modelo de regresión (Random Forest, R)")

abline(a = 0, b = 1, col = "#c0392b", lty = 2, lwd = 1.5)

legend("topleft", legend = "Predicción perfecta (y = x)",
       col = "#c0392b", lty = 2, lwd = 1.5, bty = "n", cex = 0.9)

# Cuadro de metricas (rect + text en vez de legend, que no
# calcula bien la altura de la caja con texto multilinea)
usr <- par("usr")  # xmin, xmax, ymin, ymax en coordenadas del grafico
ancho <- usr[2] - usr[1]
alto  <- usr[4] - usr[3]

x_der <- usr[2] - 0.03 * ancho
x_izq <- usr[2] - 0.30 * ancho
y_inf <- usr[3] + 0.03 * alto
y_sup <- usr[3] + 0.17 * alto

rect(x_izq, y_inf, x_der, y_sup, col = "white", border = "grey70")

texto_metricas <- sprintf("RMSE = %.2f €\nR2 = %.3f\nn = %d",
                          rmse_oob, r2_oob, nrow(validacion_regresion))
text(x = (x_izq + x_der) / 2, y = (y_inf + y_sup) / 2,
     labels = texto_metricas, cex = 0.9)

dev.off()