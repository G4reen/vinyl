import pandas as pd
import numpy as np
import os
import logging

def validar_calidad_vinilos(df):
    logging.info("[DATA QUALITY] Iniciando control de calidad y completitud del set de datos...")
    
    os.makedirs("logs", exist_ok=True)
    
    # 1. VALIDACIÓN ESTRUCTURAL
    columnas_requeridas = ['sku', 'titulo', 'artista', 'precio_clp', 'stock']
    if not all(col in df.columns for col in columnas_requeridas):
        logging.error("[DATA QUALITY] Falla Estructural: El archivo origen no contiene el esquema de columnas requerido.")
        return None
        
    logging.info("[DATA QUALITY] Verificacion Estructural: Esquema de columnas valido.")
    
    df_gestionado = df.copy()
    
    # Estandarizar valores nulos de texto
    df_gestionado['titulo'] = df_gestionado['titulo'].astype(str).str.strip()
    df_gestionado['artista'] = df_gestionado['artista'].astype(str).str.strip()
    df_gestionado['titulo'] = df_gestionado['titulo'].replace(['', 'nan', 'NAN', 'None'], np.nan)
    df_gestionado['artista'] = df_gestionado['artista'].replace(['', 'nan', 'NAN', 'None'], np.nan)

    # 2. GESTIÓN DE COMPLETITUD (TEXTOS FALTANTES)
    filtro_nulos_titulo = df_gestionado['titulo'].isna()
    filtro_nulos_artista = df_gestionado['artista'].isna()
    
    if filtro_nulos_titulo.any():
        logging.warning(f"[DATA QUALITY] Alerta de Completitud: {filtro_nulos_titulo.sum()} registros sin titulo detectados. Asignando 'UNKNOWN ALBUM' y exportando traza.")
        df_gestionado[filtro_nulos_titulo].to_csv("logs/anomalias_titulos_faltantes.log", index=False)
        df_gestionado.loc[filtro_nulos_titulo, 'titulo'] = 'UNKNOWN ALBUM'
        
    if filtro_nulos_artista.any():
        logging.warning(f"[DATA QUALITY] Alerta de Completitud: {filtro_nulos_artista.sum()} registros sin artista detectados. Asignando 'UNKNOWN ARTIST' y exportando traza.")
        df_gestionado[filtro_nulos_artista].to_csv("logs/anomalias_artistas_faltantes.log", index=False)
        df_gestionado.loc[filtro_nulos_artista, 'artista'] = 'UNKNOWN ARTIST'

    # Conversión explícita a tipos numéricos
    df_gestionado['precio_clp'] = pd.to_numeric(df_gestionado['precio_clp'], errors='coerce')
    df_gestionado['stock'] = pd.to_numeric(df_gestionado['stock'], errors='coerce')

    # 3. AISLAMIENTO DE NULOS CRÍTICOS
    filtro_insalvables = df_gestionado['sku'].isna() | df_gestionado['precio_clp'].isna()
    datos_insalvables = df_gestionado[filtro_insalvables]
    
    if not datos_insalvables.empty:
        logging.warning(f"[DATA QUALITY] Alerta de Completitud: {len(datos_insalvables)} registros omitidos por ausencia de SKU o Precio (Insalvables). Detalle en 'logs/anomalias_nulos_descartados.log'.")
        datos_insalvables.to_csv("logs/anomalias_nulos_descartados.log", index=False)
        df_gestionado = df_gestionado[~filtro_insalvables]

    # 4. DETECCIÓN Y CORRECCIÓN DE STOCK NEGATIVO
    filtro_stock_negativo = df_gestionado['stock'] < 0
    cantidad_stock_negativo = filtro_stock_negativo.sum()
    
    if cantidad_stock_negativo > 0:
        logging.warning(f"[DATA QUALITY] Alerta Semantica: {cantidad_stock_negativo} registros con stock negativo detectados. Aplicando regla de imputacion automatica a cero.")
        df_gestionado[filtro_stock_negativo].to_csv("logs/anomalias_stock_corregidas.log", index=False)
        df_gestionado.loc[filtro_stock_negativo, 'stock'] = 0

    # 5. DETECCIÓN Y CORRECCIÓN DE PRECIO NEGATIVO
    filtro_precio_negativo = df_gestionado['precio_clp'] < 0
    cantidad_precio_negativo = filtro_precio_negativo.sum()
    
    if cantidad_precio_negativo > 0:
        logging.warning(f"[DATA QUALITY] Alerta Semantica: {cantidad_precio_negativo} registros con precio negativo detectados. Aplicando conversion a valor absoluto.")
        df_gestionado[filtro_precio_negativo].to_csv("logs/anomalias_precios_corregidos.log", index=False)
        df_gestionado.loc[filtro_precio_negativo, 'precio_clp'] = df_gestionado.loc[filtro_precio_negativo, 'precio_clp'].abs()

    # 6. RECALCULO DE MÉTRICAS ENRIQUECIDAS
    df_gestionado['valor_inventario_total'] = df_gestionado['precio_clp'] * df_gestionado['stock']
    logging.info("[DATA QUALITY] Enriquecimiento: Columna 'valor_inventario_total' calculada exitosamente.")

    # 7. FILTRADO DE VALORES CERO
    datos_validos = df_gestionado[df_gestionado['precio_clp'] > 0]
    datos_criticos = df_gestionado[df_gestionado['precio_clp'] == 0]
    
    if not datos_criticos.empty:
        logging.warning(f"[DATA QUALITY] Alerta Semantica: {len(datos_criticos)} registros descartados por precio equivalente a cero. Detalle en 'logs/anomalias_precios_descartados.log'.")
        datos_criticos.to_csv("logs/anomalias_precios_descartados.log", index=False)
        
    logging.info("[DATA QUALITY] Control de calidad finalizado correctamente.")
    return datos_validos