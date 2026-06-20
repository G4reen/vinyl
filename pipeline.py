import os
import sqlite3
import logging
import pandas as pd
from datetime import datetime

# Importaciones modulares del proyecto
from ingestion.ingesta import cargar_catalogo_vinilos
from procesamiento.transformacion import limpiar_datos_vinilos
from data_quality.validador import validar_calidad_vinilos
from modelo.entrenamiento import ejecutar_entrenamiento

# Asegurar directorios locales
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Configuración del formato de logs
CONFIG_LOGS_ARCHIVO = f"logs/ejecucion_pipeline_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(CONFIG_LOGS_ARCHIVO, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def cargar_datos_incremental(df_nuevo, ruta_db):
    """
    Carga los datos nuevos en la base de datos de forma incremental.
    Si ya existen registros, combina con los anteriores y elimina duplicados por SKU.
    Así el historial se acumula en lugar de borrarse en cada ejecución.
    """
    tabla = "inventario_vinilos"
    conn = sqlite3.connect(ruta_db)

    # Verificamos si la tabla ya existe y tiene datos
    try:
        df_existente = pd.read_sql(f"SELECT * FROM {tabla}", conn)
        logging.info(f"[Carga] Se encontraron {len(df_existente)} registros existentes en la base de datos.")

        # Combinamos los datos anteriores con los nuevos
        df_combinado = pd.concat([df_existente, df_nuevo], ignore_index=True)

        # Eliminamos duplicados: si un SKU ya existe, nos quedamos con la versión más nueva
        # (la del final, que es df_nuevo)
        df_combinado = df_combinado.drop_duplicates(subset=['sku'], keep='last')

        logging.info(f"[Carga] Registros tras deduplicación incremental: {len(df_combinado)}")

    except Exception:
        # Si la tabla no existe todavía, simplemente cargamos los datos nuevos
        logging.info("[Carga] No se encontró tabla previa. Se realizará carga inicial.")
        df_combinado = df_nuevo

    # Cargamos el resultado final a la base de datos
    df_combinado.to_sql(tabla, conn, if_exists="replace", index=False)
    conn.close()

    return len(df_combinado)

def calcular_kpis(df_crudo, df_validado):
    """
    Calcula y loguea los KPIs principales del pipeline al finalizar la ejecución.
    """
    logging.info("[KPIs] ========== MÉTRICAS DE LA EJECUCIÓN ==========")

    total_origen = len(df_crudo)
    total_validos = len(df_validado)
    descartados = total_origen - total_validos

    # KPI 1: Porcentaje de registros válidos
    pct_validos = (total_validos / total_origen * 100) if total_origen > 0 else 0
    logging.info(f"[KPIs] Registros válidos: {total_validos} / {total_origen} ({pct_validos:.1f}%)")

    # KPI 2: Registros descartados
    logging.info(f"[KPIs] Registros descartados: {descartados}")

    # KPI 3: Valor total del inventario procesado
    valor_total = df_validado['valor_inventario_total'].sum()
    logging.info(f"[KPIs] Valor total del inventario procesado: ${valor_total:,.0f} CLP")

    # KPI 4: Distribución por segmento de disponibilidad
    distribucion = df_validado['segmento_disponibilidad'].value_counts()
    for segmento, cantidad in distribucion.items():
        logging.info(f"[KPIs] {segmento}: {cantidad} productos")

    logging.info("[KPIs] =================================================")

def orquestar_pipeline():
    logging.info("=====================================================================")
    logging.info("INICIANDO EJECUCIÓN DEL PIPELINE AUTOMATIZADO - VINYLFLOW")
    logging.info("=====================================================================")

    inicio = datetime.now()

    try:
        # ETAPA 1: INGESTA
        logging.info("[PIPELINE] ETAPA 1/4: Iniciando proceso de ingesta de datos...")
        df_crudo = cargar_catalogo_vinilos()
        logging.info(f"[PIPELINE] Ingesta finalizada. Registros leidos del origen: {len(df_crudo)}")
        logging.info("---------------------------------------------------------------------")

        # ETAPA 2: TRANSFORMACIÓN
        logging.info("[PIPELINE] ETAPA 2/4: Iniciando normalizacion y transformacion...")
        df_limpio = limpiar_datos_vinilos(df_crudo)
        logging.info("---------------------------------------------------------------------")

        # ETAPA 3: DATA QUALITY
        logging.info("[PIPELINE] ETAPA 3/4: Transfiriendo control al modulo de Data Quality...")
        df_validado = validar_calidad_vinilos(df_limpio)

        if df_validado is None or df_validado.empty:
            logging.error("[PIPELINE] Ejecución abortada: El set de datos no contiene registros recuperables.")
            return

        logging.info(f"[PIPELINE] Data Quality finalizado. Registros aptos para produccion: {len(df_validado)}")
        logging.info("---------------------------------------------------------------------")

        # ETAPA 4: CARGA INCREMENTAL
        logging.info("[PIPELINE] ETAPA 4/4: Iniciando carga incremental de datos...")
        ruta_db = "data/dw_vinylflow.db"

        try:
            total_cargado = cargar_datos_incremental(df_validado, ruta_db)
            logging.info(f"[PIPELINE] Carga incremental exitosa. Total registros en BD: {total_cargado}. Destino: {ruta_db}")
        except Exception as e:
            logging.error(f"[PIPELINE] Error en la carga de datos: {str(e)}")
            return

        # KPIs FINALES
        calcular_kpis(df_crudo, df_validado)

        # Tiempo total de ejecución
        fin = datetime.now()
        duracion = (fin - inicio).total_seconds()
        logging.info(f"[KPIs] Tiempo total de ejecución: {duracion:.2f} segundos")

        logging.info("=====================================================================")
        logging.info("PIPELINE FINALIZADO EXITOSAMENTE - PROCESO COMPLETADO")
        logging.info("=====================================================================")

        # ETAPA 5: ENTRENAMIENTO Y EVALUACIÓN DEL MODELO DE IA
        logging.info("[PIPELINE] ETAPA 5/5: Iniciando entrenamiento del modelo de IA...")
        try:
            ejecutar_entrenamiento()
        except Exception as e:
            logging.error(f"[PIPELINE] Error en la etapa de entrenamiento del modelo: {str(e)}")

    except Exception as e:
        logging.critical(f"[CRITICAL] Falla catastrófica en el flujo automatizado: {str(e)}")
        logging.info("=====================================================================")

if __name__ == "__main__":
    orquestar_pipeline()