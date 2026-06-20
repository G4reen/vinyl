"""
Módulo de Entrenamiento de Modelo de IA - VinylFlow Fase 2
============================================================
Objetivo de negocio:
    Predecir el RIESGO DE QUIEBRE DE STOCK (riesgo_quiebre_stock) de un
    vinilo a partir de su precio y la popularidad de su artista en el
    catálogo, SIN usar el stock como feature (evita fuga de datos / leakage,
    ya que el segmento de disponibilidad se deriva directamente del stock).

Corrección de Fase 1:
    Se detectó que 'segmento_disponibilidad' se calculaba en la etapa de
    Transformación usando el stock ANTES de que Data Quality corrigiera los
    valores negativos a 0. Este módulo recalcula el segmento usando el
    stock final ya validado, antes de derivar la variable objetivo.
"""

import os
import logging
import warnings
import pandas as pd
import numpy as np
import sqlite3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    confusion_matrix, accuracy_score, precision_score, recall_score,
    f1_score, roc_curve, roc_auc_score, classification_report
)

warnings.filterwarnings("ignore")  # silencia FutureWarning de seaborn/sklearn

RUTA_DB = "data/dw_vinylflow.db"
RUTA_RESULTADOS = "modelo/resultados"
RUTA_LOG = "logs/entrenamiento_modelo.log"

os.makedirs(RUTA_RESULTADOS, exist_ok=True)
os.makedirs("logs", exist_ok=True)

# Logger PROPIO (no el root): así no se mezclan logs internos de matplotlib,
# PIL, fontTools, etc. Solo aparece lo que este módulo registra explícitamente.
logger = logging.getLogger("vinylflow.modelo")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    _formato = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    _file_handler = logging.FileHandler(RUTA_LOG, encoding='utf-8')
    _file_handler.setFormatter(_formato)
    _stream_handler = logging.StreamHandler()
    _stream_handler.setFormatter(_formato)
    logger.addHandler(_file_handler)
    logger.addHandler(_stream_handler)

logging = logger  # permite reusar logging.info(...) sin reescribir todo el archivo


def _separador(titulo=None):
    logging.info("-" * 70)
    if titulo:
        logging.info(titulo)
        logging.info("-" * 70)


# ---------------------------------------------------------------------------
# 1. CARGA Y CORRECCIÓN DE LA VARIABLE DE SEGMENTO
# ---------------------------------------------------------------------------
def cargar_datos_validados():
    logging.info("Cargando datos validados desde el Data Warehouse...")
    conn = sqlite3.connect(RUTA_DB)
    df = pd.read_sql("SELECT * FROM inventario_vinilos", conn)
    conn.close()
    logging.info(f"Registros cargados: {len(df)}")
    return df


def recalcular_segmento(stock):
    if stock == 0:
        return "AGOTADO"
    elif stock <= 5:
        return "STOCK CRITICO"
    else:
        return "STOCK SALUDABLE"


def preparar_dataset(df):
    _separador("ETAPA 5.1 — PREPARACIÓN DEL DATASET PARA MODELADO")
    logging.info("Recalculando segmento_disponibilidad con stock final (corrección de bug Fase 1)...")
    df = df.copy()
    segmento_original = df["segmento_disponibilidad"].copy()
    df["segmento_disponibilidad"] = df["stock"].apply(recalcular_segmento)

    discrepancias = (segmento_original != df["segmento_disponibilidad"]).sum()
    logging.warning(f"Registros con segmento corregido respecto a Fase 1: {discrepancias}")

    # Variable objetivo binaria
    df["riesgo_quiebre_stock"] = df["segmento_disponibilidad"].isin(
        ["AGOTADO", "STOCK CRITICO"]
    ).astype(int)

    # Feature de popularidad del artista (frequency encoding) - NO usa stock
    frecuencia_artista = df["artista"].value_counts()
    df["frecuencia_artista"] = df["artista"].map(frecuencia_artista)

    dist = df["riesgo_quiebre_stock"].value_counts()
    logging.info(f"Variable objetivo 'riesgo_quiebre_stock' -> Sin riesgo: {dist.get(0,0)} | Con riesgo: {dist.get(1,0)}")
    return df


# ---------------------------------------------------------------------------
# 2. ANÁLISIS DE CALIDAD DE DATOS (media, moda, percentiles, nulos)
# ---------------------------------------------------------------------------
def analisis_calidad_datos(df):
    _separador("ETAPA 5.2 — ANÁLISIS DE CALIDAD DE DATOS (nulos, moda, percentiles)")

    nulos = df[["precio_clp", "frecuencia_artista", "stock"]].isnull().sum()
    if nulos.sum() == 0:
        logging.info("Nulos detectados: 0 (ya imputados en Fase 1 - Data Quality: "
                      "'UNKNOWN ARTIST'/'UNKNOWN ALBUM' en categóricos, precio/stock negativos corregidos)")
    else:
        logging.warning(f"Nulos remanentes detectados, se imputa con la mediana:\n{nulos.to_string()}")
        for col in ["precio_clp", "frecuencia_artista"]:
            df[col] = df[col].fillna(df[col].median())

    for col in ["precio_clp", "frecuencia_artista"]:
        moda = df[col].mode().iloc[0]
        p = df[col].quantile([0.10, 0.25, 0.50, 0.75, 0.90])
        logging.info(f"{col:<20} moda={moda:>10.2f} | P10={p[0.10]:>10.2f} P25={p[0.25]:>10.2f} "
                      f"P50={p[0.50]:>10.2f} P75={p[0.75]:>10.2f} P90={p[0.90]:>10.2f}")

    return df


# ---------------------------------------------------------------------------
# 3. ANÁLISIS UNIVARIADO Y BIVARIADO
# ---------------------------------------------------------------------------
def _formato_clp(valor, _pos=None):
    return f"${valor:,.0f}".replace(",", ".")


def analisis_exploratorio(df):
    _separador("ETAPA 5.3 — ANÁLISIS UNIVARIADO")
    for col in ["precio_clp", "frecuencia_artista"]:
        desc = df[col].describe()
        logging.info(f"{col:<20} media={desc['mean']:>10.2f} mediana={df[col].median():>10.2f} "
                      f"std={desc['std']:>9.2f} min={desc['min']:>10.2f} max={desc['max']:>10.2f}")

    dist_pct = (df['riesgo_quiebre_stock'].value_counts(normalize=True) * 100).round(1)
    logging.info(f"Distribución riesgo_quiebre_stock -> Sin riesgo: {dist_pct.get(0,0)}% | Con riesgo: {dist_pct.get(1,0)}%")

    # --- Gráfico 1: Salud del catálogo (el dato de negocio real, no una variable abstracta) ---
    conteo_segmento = df["segmento_disponibilidad"].value_counts().reindex(
        ["STOCK SALUDABLE", "STOCK CRITICO", "AGOTADO"]).fillna(0).astype(int)
    colores_segmento = {"STOCK SALUDABLE": "#4CAF50", "STOCK CRITICO": "#FF9800", "AGOTADO": "#F44336"}

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    bars = axes[0].bar(conteo_segmento.index, conteo_segmento.values,
                        color=[colores_segmento[s] for s in conteo_segmento.index],
                        edgecolor="white", linewidth=1.5)
    axes[0].set_title("¿Cómo está el stock del catálogo HOY?", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("Cantidad de vinilos")
    for b, v in zip(bars, conteo_segmento.values):
        axes[0].text(b.get_x() + b.get_width()/2, v + 2, str(v), ha="center", fontweight="bold")
    axes[0].set_ylim(0, conteo_segmento.max() * 1.15)

    valor_por_segmento = df.groupby("segmento_disponibilidad")["valor_inventario_total"].sum().reindex(
        ["STOCK SALUDABLE", "STOCK CRITICO", "AGOTADO"]).fillna(0)
    axes[1].pie(conteo_segmento.values, labels=[f"{s}\n({v} vinilos)" for s, v in conteo_segmento.items()],
                autopct="%1.0f%%", colors=[colores_segmento[s] for s in conteo_segmento.index], startangle=90)
    axes[1].set_title("Proporción del catálogo en riesgo", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(f"{RUTA_RESULTADOS}/01_salud_catalogo.png", dpi=150)
    plt.close()

    # --- Gráfico 2: las 2 variables que SÍ usa el modelo, en términos de negocio ---
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    axes[0].hist(df["precio_clp"], bins=15, color="#2c5f8a", edgecolor="white")
    axes[0].axvline(df["precio_clp"].median(), color="#F44336", linestyle="--",
                     label=f"Mediana: {_formato_clp(df['precio_clp'].median())}")
    axes[0].set_title("¿A qué precio se vende el catálogo?", fontsize=12, fontweight="bold")
    axes[0].set_xlabel("Precio de venta (CLP)")
    axes[0].set_ylabel("Cantidad de vinilos")
    axes[0].xaxis.set_major_formatter(plt.FuncFormatter(_formato_clp))
    axes[0].legend(fontsize=9)

    top_artistas = df.drop_duplicates("artista").nlargest(10, "frecuencia_artista")[["artista", "frecuencia_artista"]]
    top_artistas = top_artistas.sort_values("frecuencia_artista")
    axes[1].barh(top_artistas["artista"], top_artistas["frecuencia_artista"], color="#8a2c2c")
    axes[1].set_title("Top 10 artistas con más títulos en catálogo", fontsize=12, fontweight="bold")
    axes[1].set_xlabel("Cantidad de títulos en el catálogo")
    plt.tight_layout()
    plt.savefig(f"{RUTA_RESULTADOS}/02_variables_predictoras.png", dpi=150)
    plt.close()

    _separador("ETAPA 5.4 — ANÁLISIS BIVARIADO Y MATRIZ DE CORRELACIÓN")
    corr = df[["precio_clp", "frecuencia_artista", "riesgo_quiebre_stock"]].rename(columns={
        "precio_clp": "Precio", "frecuencia_artista": "Popularidad artista", "riesgo_quiebre_stock": "Riesgo quiebre"
    }).corr().round(3)
    for linea in corr.to_string().split("\n"):
        logging.info(f"  {linea}")

    # --- Gráfico 3: ¿el precio o la popularidad SEPARAN a los vinilos en riesgo? ---
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    sns.heatmap(corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1, fmt=".2f", ax=axes[0], cbar=False)
    axes[0].set_title("Matriz de correlación", fontsize=12, fontweight="bold")

    colores_riesgo = {0: "#4CAF50", 1: "#F44336"}
    sns.stripplot(data=df, x="precio_clp", y="frecuencia_artista", hue="riesgo_quiebre_stock",
                  orient="h", palette=colores_riesgo, alpha=0.55, jitter=0.3, size=5, ax=axes[1])
    axes[1].set_title("¿Se ven separados los vinilos en riesgo?", fontsize=12, fontweight="bold")
    axes[1].set_xlabel("Precio (CLP)")
    axes[1].set_ylabel("Popularidad del artista (títulos en catálogo)")
    axes[1].xaxis.set_major_formatter(plt.FuncFormatter(_formato_clp))
    handles, _ = axes[1].get_legend_handles_labels()
    axes[1].legend(handles, ["Sin riesgo", "Con riesgo"], fontsize=9, title=None)
    plt.tight_layout()
    plt.savefig(f"{RUTA_RESULTADOS}/03_bivariado_precio_riesgo.png", dpi=150)
    plt.close()


# ---------------------------------------------------------------------------
# 3. ENTRENAMIENTO Y COMPARACIÓN DE MODELOS
# ---------------------------------------------------------------------------
def entrenar_y_comparar(df):
    _separador("ETAPA 5.5 — PARTICIÓN Y ESCALAMIENTO DE DATOS")
    X = df[["precio_clp", "frecuencia_artista"]]
    y = df["riesgo_quiebre_stock"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    logging.info(f"Train: {len(X_train)} registros ({len(X_train)/len(df)*100:.0f}%) | "
                 f"Test: {len(X_test)} registros ({len(X_test)/len(df)*100:.0f}%) | stratify=y")

    escalador = StandardScaler()
    X_train_esc = escalador.fit_transform(X_train)
    X_test_esc = escalador.transform(X_test)

    _separador("ETAPA 5.6 — JUSTIFICACIÓN DE ELECCIÓN DE ALGORITMOS")
    logging.info("1) Regresion_Logistica: modelo lineal interpretable, bajo riesgo de sobreajuste")
    logging.info("   en un dataset pequeño (244 registros). Se usa como modelo BASE/baseline.")
    logging.info("2) Random_Forest: ensamble no lineal, capaz de capturar interacciones entre")
    logging.info("   variables. max_depth=4 limita el sobreajuste. Verifica si una relación")
    logging.info("   no lineal mejora el resultado respecto al baseline.")
    logging.info("Ambos usan class_weight='balanced' (clase riesgo=1 es solo ~27% de los datos).")
    logging.info("Criterio de selección final: mayor AUC en test (robusto frente a clases desbalanceadas).")

    modelos = {
        "Regresion_Logistica": LogisticRegression(class_weight="balanced", random_state=42),
        "Random_Forest": RandomForestClassifier(n_estimators=200, max_depth=4, class_weight="balanced", random_state=42),
    }

    resultados = {}
    for nombre, modelo in modelos.items():
        modelo.fit(X_train_esc, y_train)
        y_pred = modelo.predict(X_test_esc)
        y_prob = modelo.predict_proba(X_test_esc)[:, 1]

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_prob)
        gini = 2 * auc - 1
        cm = confusion_matrix(y_test, y_pred)
        cm_df = pd.DataFrame(cm, index=["Real: Sin riesgo", "Real: Con riesgo"],
                              columns=["Pred: Sin riesgo", "Pred: Con riesgo"])

        _separador(f"RESULTADOS — {nombre}")
        logging.info(f"Accuracy={acc:.3f}  Precision={prec:.3f}  Recall={rec:.3f}  "
                      f"F1={f1:.3f}  AUC={auc:.3f}  Gini={gini:.3f}")
        logging.info("Matriz de confusión:")
        for linea in cm_df.to_string().split("\n"):
            logging.info(f"  {linea}")
        logging.info("Reporte de clasificación:")
        reporte = classification_report(y_test, y_pred, target_names=["Sin riesgo", "Con riesgo"], zero_division=0)
        for linea in reporte.split("\n"):
            if linea.strip():
                logging.info(f"  {linea}")

        resultados[nombre] = {
            "modelo": modelo, "accuracy": acc, "precision": prec, "recall": rec,
            "f1": f1, "auc": auc, "gini": gini, "cm": cm,
            "y_test": y_test, "y_prob": y_prob
        }

    mejor_modelo = max(resultados, key=lambda k: resultados[k]["auc"])
    _separador(f"MODELO SELECCIONADO POR MEJOR AUC: {mejor_modelo}")

    _graficar_comparacion(resultados, mejor_modelo)
    return resultados, mejor_modelo


def _graficar_comparacion(resultados, mejor_modelo):
    # Matrices de confusión, con etiquetas de negocio y porcentajes
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    etiquetas_negocio = np.array([["Descartado\ncorrectamente", "Reposición\ninnecesaria (FP)"],
                                   ["Venta perdida\nno detectada (FN)", "Riesgo\ndetectado a tiempo"]])
    for ax, (nombre, r) in zip(axes, resultados.items()):
        cm = r["cm"]
        cm_pct = cm / cm.sum() * 100
        anotaciones = np.array([[f"{cm[i,j]}\n({cm_pct[i,j]:.0f}%)\n{etiquetas_negocio[i,j]}"
                                  for j in range(2)] for i in range(2)])
        sns.heatmap(cm, annot=anotaciones, fmt="", cmap="Blues", ax=ax, cbar=False,
                    xticklabels=["Pred: Sin riesgo", "Pred: Con riesgo"],
                    yticklabels=["Real: Sin riesgo", "Real: Con riesgo"], annot_kws={"fontsize": 8.5})
        ax.set_title(f"{nombre}", fontsize=12, fontweight="bold")
    fig.suptitle("Matriz de Confusión — ¿Qué tan caro es cada error para VinylFlow?", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(f"{RUTA_RESULTADOS}/04_matrices_confusion.png", dpi=150)
    plt.close()

    # Curva ROC con zona de azar resaltada
    plt.figure(figsize=(6.5, 5.5))
    plt.fill_between([0, 1], [0, 1], color="gray", alpha=0.15, label="Zona de azar (no mejor que adivinar)")
    for nombre, r in resultados.items():
        fpr, tpr, _ = roc_curve(r["y_test"], r["y_prob"])
        estilo = "-" if nombre == mejor_modelo else "--"
        ancho = 2.5 if nombre == mejor_modelo else 1.5
        plt.plot(fpr, tpr, estilo, linewidth=ancho, label=f"{nombre} (AUC={r['auc']:.3f}, Gini={r['gini']:.3f})")
    plt.plot([0, 1], [0, 1], "k:", label="Azar puro (AUC=0.5)")
    plt.xlabel("Tasa de Falsos Positivos")
    plt.ylabel("Tasa de Verdaderos Positivos")
    plt.title("Curva ROC — ¿Predice mejor que tirar una moneda?", fontsize=12, fontweight="bold")
    plt.legend(fontsize=8, loc="lower right")
    plt.tight_layout()
    plt.savefig(f"{RUTA_RESULTADOS}/05_curva_roc.png", dpi=150)
    plt.close()

    # Comparación de métricas, con Recall destacado (la métrica clave del negocio)
    metricas_df = pd.DataFrame({
        n: {"Accuracy": r["accuracy"], "Precision": r["precision"], "Recall": r["recall"],
            "F1": r["f1"], "AUC": r["auc"]} for n, r in resultados.items()
    }).T
    metricas_df.to_csv(f"{RUTA_RESULTADOS}/comparacion_metricas.csv")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    metricas_df.plot(kind="bar", ax=ax, colormap="viridis")
    ax.axhline(y=0.5, color="red", linestyle="--", alpha=0.6, label="Umbral de azar (0.5)")
    ax.set_title("Comparación de Métricas — Recall es la más relevante\n"
                 "(detectar a tiempo un vinilo que se queda sin stock)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Valor")
    ax.set_xticklabels(metricas_df.index, rotation=0)
    ax.legend(loc="upper right", fontsize=8)
    plt.tight_layout()
    plt.savefig(f"{RUTA_RESULTADOS}/06_comparacion_metricas.png", dpi=150)
    plt.close()


# ---------------------------------------------------------------------------
# 4. ORQUESTACIÓN
# ---------------------------------------------------------------------------
def ejecutar_entrenamiento():
    _separador("INICIANDO ETAPA 5: ENTRENAMIENTO Y EVALUACIÓN DEL MODELO DE IA")

    df_crudo = cargar_datos_validados()
    df = preparar_dataset(df_crudo)
    df = analisis_calidad_datos(df)
    analisis_exploratorio(df)
    resultados, mejor_modelo = entrenar_y_comparar(df)

    _separador("RESUMEN FINAL")
    logging.info(f"{'Modelo':<22}{'Accuracy':>10}{'Precision':>11}{'Recall':>9}{'F1':>8}{'AUC':>8}{'Gini':>8}")
    for nombre, r in resultados.items():
        marca = " <- recomendado" if nombre == mejor_modelo else ""
        logging.info(f"{nombre:<22}{r['accuracy']:>10.3f}{r['precision']:>11.3f}{r['recall']:>9.3f}"
                      f"{r['f1']:>8.3f}{r['auc']:>8.3f}{r['gini']:>8.3f}{marca}")
    logging.info("Gráficos y métricas exportados en 'modelo/resultados/'")
    _separador("ENTRENAMIENTO FINALIZADO")
    return resultados, mejor_modelo


if __name__ == "__main__":
    ejecutar_entrenamiento()
