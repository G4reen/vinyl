import sqlite3
import os
from ingestion.ingesta import cargar_catalogo_vinilos
from procesamiento.transformacion import limpiar_datos_vinilos
from data_quality.validador import validar_calidad_vinilos

def orquestar_pipeline():
    print("=== INICIANDO PIPELINE REAL MODULAR (VINYLFLOW) ===")
    
    # Aseguramos la existencia de las carpetas operativas
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    try:
        # 1. INGESTA
        df_crudo = cargar_catalogo_vinilos()
        
        # 2. PROCESAMIENTO
        df_limpio = limpiar_datos_vinilos(df_crudo)
        
        # 3. VALIDACION
        df_validado = validar_calidad_vinilos(df_limpio)
        
        # 4. CARGA (Base de datos relacional)
        ruta_db = "data/dw_vinylflow.db"
        print(f"[Carga] Insertando datos limpios en la base de datos: {ruta_db}")
        
        conn = sqlite3.connect(ruta_db)
        # Cargamos los datos en la tabla 'inventario_vinilos'. Si ya existe, la reemplaza.
        df_validado.to_sql("inventario_vinilos", conn, if_exists="replace", index=False)
        conn.close()
        
        print("🚀 ¡Pipeline ejecutado con datos reales y finalizado con éxito!")
        
    except Exception as e:
        print(f" El pipeline falló catastróficamente de forma controlada: {e}")

if __name__ == "__main__":
    orquestar_pipeline()