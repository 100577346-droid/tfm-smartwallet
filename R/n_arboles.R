library(randomForest)
library(dplyr)

# ---- 1. Cargar y preparar los datos ------------------------
df <- read.csv2("D:/Master/TFM/DATOS/union_dataset.csv", stringsAsFactors = FALSE, dec = ",")

# Subconjunto de clientes que tienen adoptada la wallet de stablecoins
df_adoptantes <- df %>% filter(adoptado == 1)

# Variables predictoras.
# Se excluye "adoptado" por ser constante dentro de este subconjunto (no aporta informacion).
# Se excluye "gasto_SC" del conjunto de predictores por ser la variable objetivo.
# Se excluyen identificadores/variables no predictivas (idCliente, cp).
# Se excluye "tipo_empleo": la Practica 2 (Fig. 6 solucion, boxplot de
# gasto_SC) confirmo que el gasto en stablecoins no depende del tipo de
# empleo, igual que se descarto para el clustering.
vars_predictoras <- c("edad", "latitud_hogar", "longitud_hogar",
                      "nivel_estudios", "usa_fintech", "hipoteca_imp_inicial",
                      "hipoteca_impagada", "numero_hijos", "edad_hijo_mayor",
                      "antiguedad_anos", "tiene_hijos", "suma_ingresos",
                      "tiene_ingresos_declarados", "num_movimientos_gasto",
                      "gasto_Alimentacion", "gasto_Amazon", "gasto_Centro_deportivo",
                      "gasto_Gaming", "gasto_Inversion", "gasto_Moda",
                      "gasto_Ocio_Nocturno", "gasto_Restaurante", "gasto_Seguro",
                      "gasto_Suscripcion", "gasto_Transferencia_Internacional")

var_objetivo <- "gasto_SC"

datos <- df_adoptantes[, c(vars_predictoras, var_objetivo)]
datos <- na.omit(datos)

# Variables de tipo texto -> factor (randomForest las necesita como factor, no character)
vars_categoricas <- c("nivel_estudios")
datos[vars_categoricas] <- lapply(datos[vars_categoricas], as.factor)

# ---- 2. Rango de numero de arboles a evaluar ----------------
k_range <- seq(50, 1000, by = 50)
set.seed(1992)

# Se entrena un unico modelo con el numero maximo de arboles y OOB activado;
# el error OOB para cada k intermedio se extrae directamente de ese mismo
# modelo (evita reentrenar 20 veces, igual que se evito recalcular la
# matriz de distancias en el codigo de k-means)
rf_completo <- randomForest(
  x = datos[, vars_predictoras],
  y = datos[[var_objetivo]],
  ntree = max(k_range),
  mtry = max(floor(length(vars_predictoras) / 3), 1),
  importance = FALSE,
  do.trace = TRUE
)

resultados <- data.frame(
  k = integer(),
  oob_mse = numeric(),
  oob_rmse = numeric()
)

# ---- 3. Loop: error OOB acumulado para cada k ---------------
for (k in k_range) {
  
  oob_mse_k <- rf_completo$mse[k]
  oob_rmse_k <- sqrt(oob_mse_k)
  
  resultados <- rbind(resultados, data.frame(
    k = k,
    oob_mse = oob_mse_k,
    oob_rmse = oob_rmse_k
  ))
  
  cat(sprintf("k=%d | OOB MSE=%.3f | OOB RMSE=%.3f\n",
              k, oob_mse_k, oob_rmse_k))
}

print(resultados)

# ---- 4. Guardar resultados a CSV -----------------------------
write.csv2(resultados,"D:/Master/TFM/DATOS/resultados_validacion_num_arboles.csv", row.names = FALSE)

# ---- 5. Grafico homogeneizado ---------------------------------
# Evolucion del error OOB (RMSE) segun el numero de arboles
par(mar = c(5, 6.5, 4, 2))
plot(resultados$k, resultados$oob_rmse, type = "b", pch = 19,
     xaxt = "n",
     yaxt = "n",
     bty = "l",
     xlab = "Numero de arboles (k)",
     ylab = "",
     main = "Error OOB segun el numero de arboles")
axis(side = 1, at = resultados$k, cex.axis = 0.7, las = 2)
axis(side = 2, las = 1, cex.axis = 0.6)
mtext("OOB RMSE", side = 2, line = 4.5, cex = 0.9)

# Restaurar margenes por defecto
par(mar = c(5, 4, 4, 2) + 0.1)