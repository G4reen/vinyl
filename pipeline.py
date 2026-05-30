import os
import sqlite3
import logging
from datetime import datetime

# Importaciones modulares del proyecto
from ingestion.ingesta import cargar_catalogo_vinilos
from procesamiento.transformacion import limpiar_datos_vinilos
from data_quality.validador import validar_calidad_vinilos

# Asegurar directorios locales
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Configuración del formato de logs corporativo
CONFIG_LOGS_ARCHIVO = f"logs/ejecucion_pipeline_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(CONFIG_LOGS_ARCHIVO, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def orquestar_pipeline():
    logging.info("=====================================================================")
    logging.info("INICIANDO EJECUCIÓN DEL PIPELINE AUTOMATIZADO - VINYLFLOW")
    logging.info("=====================================================================")
    
    try:
        # ETAPA 1: INGESTA
        logging.info("[PIPELINE] ETAPA 1/4: Iniciando proceso de ingesta de datos...")
        df_crudo = cargar_catalogo_vinilos()
        logging.info(f"[PIPELINE] Ingesta finalizada. Registros leidos del origen: {len(df_crudo)}")
        logging.info("---------------------------------------------------------------------")
        
        # ETAPA 2: PROCESAMIENTO
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
        
        # ETAPA 4: CARGA
        logging.info("[PIPELINE] ETAPA 4/4: Iniciando la carga de datos...")
        ruta_db = "data/dw_vinylflow.db"
        
        conn = sqlite3.connect(ruta_db)
        df_validado.to_sql("inventario_vinilos", conn, if_exists="replace", index=False)
        conn.close()
        
        logging.info(f"[PIPELINE] Carga de datos realizada con exito. Destino: {ruta_db}")
        logging.info("=====================================================================")
        logging.info("PIPELINE FINALIZADO EXITOSAMENTE - PROCESO COMPLETADO")
        logging.info("=====================================================================")
        
    except Exception as e:
        logging.critical(f"[CRITICAL] Falla catastrofica en el flujo automatizado: {str(e)}")
        logging.info("=====================================================================")

if __name__ == "__main__":
    orquestar_pipeline()