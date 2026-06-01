import pandas as pd
import os
import logging

def cargar_catalogo_vinilos():
    ruta_csv = "data/vinilos.csv"
    logging.info(f"[Ingesta] Leyendo archivo físico desde: {ruta_csv}")

    if not os.path.exists(ruta_csv):
        raise FileNotFoundError(f"Error crítico: No se encontró el archivo {ruta_csv}")

    df = pd.read_csv(ruta_csv)
    logging.info(f"[Ingesta] Ingesta exitosa. Registros leídos del CSV: {len(df)}")
    return df