import pandas as pd

def validar_calidad_vinilos(df):
    print("[Data Quality] Iniciando chequeo de calidad del dato...")
    
    # 1. VALIDACIÓN ESTRUCTURAL
    columnas_requeridas = ['sku', 'titulo', 'artista', 'precio_clp', 'stock']
    if not all(col in df.columns for col in columnas_requeridas):
        print("Falla Estructural: El CSV no contiene todas las columnas requeridas.")
        return None
        
    print("  -> Estructura valida: Todas las columnas requeridas estan presentes.")
    
    # Creamos una copia para evitar modificar el DataFrame original de forma imprevista
    df_gestionado = df.copy()
    
    # 2. DETECCIÓN Y CORRECCIÓN DE ANOMALÍAS DE STOCK (Imputación)
    # Identificamos las filas donde el stock es negativo
    filtro_stock_negativo = df_gestionado['stock'] < 0
    cantidad_stock_negativo = filtro_stock_negativo.sum()
    
    if cantidad_stock_negativo > 0:
        print(f"Advertencia Semantica: Se detectaron {cantidad_stock_negativo} registros con stock negativo. Aplicando correccion automatica a cero.")
        
        # Registramos en el log las filas antes de ser corregidas para auditoria
        anomalias_stock = df_gestionado[filtro_stock_negativo]
        anomalias_stock.to_csv("logs/anomalias_stock_corregidas.log", index=False)
        
        # Aplicamos la correccion: forzar a 0 los valores negativos
        df_gestionado.loc[filtro_stock_negativo, 'stock'] = 0
        print("  -> Valores de stock negativo corregidos a 0. Historial guardado en 'logs/anomalias_stock_corregidas.log'.")

    # 3. VALIDACIÓN SEMÁNTICA DE PRECIOS (Filtrado exhaustivo)
    # Mantenemos la regla de eliminar registros con precios invalidos (menores o iguales a cero)
    datos_validos = df_gestionado[df_gestionado['precio_clp'] > 0]
    datos_invalidos = df_gestionado[df_gestionado['precio_clp'] <= 0]
    
    if not datos_invalidos.empty:
        print(f"Alerta Semantica: Se aislaron {len(datos_invalidos)} registros con precios erroneos.")
        datos_invalidos.to_csv("logs/anomalias_precios_detectadas.log", index=False)
        print("  -> Registros con precios invalidos aislados en 'logs/anomalias_precios_detectadas.log'")
        
    return datos_validos