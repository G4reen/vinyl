import pandas as pd
import os

def cargar_catalogo_vinilos():
    ruta_csv = "data/vinilos.csv"
    print(f"[Ingesta] Leyendo archivo físico desde: {ruta_csv}")
    
    # Verificamos si el archivo realmente existe antes de leerlo (Control de anomalías)
    if not os.path.exists(ruta_csv):
        raise FileNotFoundError(f" Error crítico: No se encontró el archivo {ruta_csv}")
        
    df = pd.read_csv(ruta_csv)
    print(f"-> Ingesta exitosa. Registros leídos del CSV: {len(df)}")
    return df