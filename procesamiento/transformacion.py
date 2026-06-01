import pandas as pd
import logging

def limpiar_datos_vinilos(df):
    logging.info("[Transformacion] Iniciando fase de transformacion y normalizacion...")

    df_transformado = df.copy()

    # 1. Eliminar duplicados por SKU
    df_transformado = df_transformado.drop_duplicates(subset=['sku'])

    # 2. Normalizar texto
    df_transformado['titulo'] = df_transformado['titulo'].astype(str).str.strip().str.upper()
    df_transformado['artista'] = df_transformado['artista'].astype(str).str.strip().str.upper()

    # 3. Convertir tipos numéricos
    df_transformado['precio_clp'] = pd.to_numeric(df_transformado['precio_clp'], errors='coerce')
    df_transformado['stock'] = pd.to_numeric(df_transformado['stock'], errors='coerce')

    df_transformado['precio_clp'] = df_transformado['precio_clp'].fillna(0)
    df_transformado['stock'] = df_transformado['stock'].fillna(0)

    # 4. Columnas derivadas
    df_transformado['valor_inventario_total'] = df_transformado['precio_clp'] * df_transformado['stock']

    def categorizar_stock(cantidad):
        if cantidad == 0:
            return 'AGOTADO'
        elif cantidad <= 5:
            return 'STOCK CRITICO'
        else:
            return 'STOCK SALUDABLE'

    df_transformado['segmento_disponibilidad'] = df_transformado['stock'].apply(categorizar_stock)

    logging.info(f"[Transformacion] Finalizada. Columnas actuales: {list(df_transformado.columns)}")
    return df_transformado