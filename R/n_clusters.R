library(cluster)      # silhouette()
library(clusterSim)   # index.DB() -> Davies-Bouldin
library(factoextra)   # graficos opcionales
library(dplyr)
library(fastDummies)  # dummy_cols() para nivel_estudios

# ---- 1. Cargar y preparar los datos ------------------------
df <- read.csv2("D:/Master/TFM/DATOS/union_dataset.csv", stringsAsFactors = FALSE, dec = ",")

df_adoptantes <- df %>% filter(adoptado == 1)

# ---- 2. Variable agregada de gasto -------------------------
# Se agrupan en un unico indicador las categorias de gasto que aportan
# poca informacion adicional una vez que "edad" ya esta en vars_perfil
# (Ocio_Nocturno y Gaming son las unicas categorias que diferenciaban
# claramente por edad en la Practica 2, Fig. 2 solucion, por lo que su
# señal queda ya recogida por la variable edad). Se mantienen separadas
# Inversion y Transferencia_Internacional por su peso economico y porque
# representan comportamientos financieros distintos entre si.
vars_resto <- c("gasto_Alimentacion", "gasto_Amazon", "gasto_Centro_deportivo",
                "gasto_Gaming", "gasto_Moda", "gasto_Ocio_Nocturno",
                "gasto_Restaurante", "gasto_Seguro", "gasto_Suscripcion")

df_adoptantes$gasto_total_resto <- rowSums(df_adoptantes[, vars_resto], na.rm = TRUE)

# Variables de perfil.
# Se excluye "tipo_empleo": la Practica 2 (Fig. 6 solucion, boxplot de
# gasto_SC) confirmo que el nivel de gasto no depende del tipo de empleo.
# Se mantiene "nivel_estudios": la Fig. 9 (solucion) muestra una tasa de
# adopcion ligeramente superior en Grado/Postgrado dentro de cada tramo
# de edad.
# Se incluye "hipoteca_impagada": la Fig. 6 (solucion) confirma que
# determina un gasto en stablecoins nulo.
# Se incluye "num_movimientos_gasto" como medida de actividad financiera.
vars_perfil <- c("edad", "latitud_hogar", "longitud_hogar",
                 "usa_fintech", "nivel_estudios", "hipoteca_impagada",
                 "num_movimientos_gasto",
                 "gasto_Inversion", "gasto_Transferencia_Internacional",
                 "gasto_total_resto")

# Variables monetarias/de conteo con cola larga -> log1p antes de escalar.
# (edad, latitud, longitud y las binarias/dummy se dejan en su escala)
vars_log <- c("num_movimientos_gasto", "gasto_Inversion",
              "gasto_Transferencia_Internacional", "gasto_total_resto")

datos <- df_adoptantes[, vars_perfil]
datos <- na.omit(datos)

datos[vars_log] <- lapply(datos[vars_log], function(x) log1p(pmax(x, 0)))

# nivel_estudios -> dummy (variable categorica, no ordinal en cuanto a
# distancia euclidea; se expande en columnas 0/1)
datos <- dummy_cols(datos, select_columns = "nivel_estudios",
                    remove_selected_columns = TRUE,
                    remove_first_dummy = TRUE)

# ---- 3. Normalizar (Z-transformation) ----------------------
datos_z <- scale(datos)

# ---- 4. Rango de k a evaluar --------------------------------
k_range <- 2:15
set.seed(1992)

# Matriz de distancias completa, se calcula UNA vez fuera del loop y se
# reutiliza en cada k (evita recalcularla 14 veces)
dist_completa <- dist(datos_z)

resultados <- data.frame(
  k = integer(),
  wcss = numeric(),
  davies_bouldin = numeric(),
  silhouette = numeric()
)

# ---- 5. Loop: k-means + las 3 metricas para cada k ----------
for (k in k_range) {
  
  km <- kmeans(datos_z, centers = k, nstart = 25, iter.max = 100)
  
  wcss_avg <- km$tot.withinss / nrow(datos_z)
  db <- index.DB(datos_z, km$cluster)$DB
  
  sil <- silhouette(km$cluster, dist_completa)
  sil_avg <- mean(sil[, 3])
  
  resultados <- rbind(resultados, data.frame(
    k = k,
    wcss = wcss_avg,
    davies_bouldin = db,
    silhouette = sil_avg
  ))
  
  cat(sprintf("k=%d | WCSS medio=%.3f | Davies-Bouldin=%.3f | Silhouette=%.3f\n",
              k, wcss_avg, db, sil_avg))
}

print(resultados)

# ---- 6. Guardar resultados a CSV -----------------------------
write.csv2(resultados,  "D:/Master/TFM/DATOS/resultados_validacion_clusters.csv", row.names = FALSE)

# ---- 7. Graficos homogeneizados ------------------------------
# 7.1 Grafica del Codo (WCSS)
par(mar = c(5, 6.5, 4, 2))
plot(resultados$k, resultados$wcss, type = "b", pch = 19,
     xaxt = "n",
     yaxt = "n",
     bty = "l",
     xlab = "Numero de clusters (k)",
     ylab = "",
     main = "Metodo del codo (WCSS medio)")
axis(side = 1, at = resultados$k, cex.axis = 0.8)
axis(side = 2, las = 1, cex.axis = 0.6)
mtext("WCSS medio", side = 2, line = 4.5, cex = 0.9)

# 7.2 Grafica de Davies-Bouldin
par(mar = c(5, 6.5, 4, 2))
plot(resultados$k, resultados$davies_bouldin, type = "b", pch = 19,
     xaxt = "n",
     yaxt = "n",
     bty = "l",
     xlab = "Numero de clusters (k)",
     ylab = "",
     main = "Indice Davies-Bouldin (menor es mejor)")
axis(side = 1, at = resultados$k, cex.axis = 0.8)
axis(side = 2, las = 1, cex.axis = 0.6)
mtext("Davies-Bouldin", side = 2, line = 4.5, cex = 0.9)

# 7.3 Grafica de Silueta Media
par(mar = c(5, 6.5, 4, 2))
plot(resultados$k, resultados$silhouette, type = "b", pch = 19,
     xaxt = "n",
     yaxt = "n",
     bty = "l",
     xlab = "Numero de clusters (k)",
     ylab = "",
     main = "Coeficiente de silueta medio")
axis(side = 1, at = resultados$k, cex.axis = 0.8)
axis(side = 2, las = 1, cex.axis = 0.6)
mtext("Silueta media", side = 2, line = 4.5, cex = 0.9)

# Restaurar margenes por defecto
par(mar = c(5, 4, 4, 2) + 0.1)