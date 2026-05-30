import pandas as pd

def limpiar_datos_vinilos(df):
    print("[Procesamiento] Iniciando fase avanzada de transformacion y normalizacion...")
    
    # Creamos una copia explícita para evitar advertencias de asignación de Pandas
    df_transformado = df.copy()
    
    # 1. ELIMINACIÓN DE DUPLICADOS EN LA LLAVE PRIMARIA
    # Asegura la unicidad de los registros basándose en el código SKU
    df_transformado = df_transformado.drop_duplicates(subset=['sku'])
    
    # 2. NORMALIZACIÓN Y ESTANDARIZACIÓN DE TEXTO
    # Convertimos a mayúsculas y eliminamos espacios en los extremos para evitar inconsistencias
    df_transformado['titulo'] = df_transformado['titulo'].astype(str).str.strip().str.upper()
    df_transformado['artista'] = df_transformado['artista'].astype(str).str.strip().str.upper()
    
    # 3. CONVERSIÓN EXPLÍCITA DE TIPOS (Data Casting)
    # Garantiza que las operaciones numéricas posteriores no fallen por discrepancia de tipos
    df_transformado['precio_clp'] = pd.to_numeric(df_transformado['precio_clp'], errors='coerce')
    df_transformado['stock'] = pd.to_numeric(df_transformado['stock'], errors='coerce')
    
    # Reemplazamos posibles valores nulos (NaN) generados por fallas en el origen por valores por defecto
    df_transformado['precio_clp'] = df_transformado['precio_clp'].fillna(0)
    df_transformado['stock'] = df_transformado['stock'].fillna(0)
    
    # 4. ENRIQUECIMIENTO DEL DATO (Columnas Derivadas de Valor de Negocio)
    # Métrica A: Valorización financiera del stock disponible en la bodega
    df_transformado['valor_inventario_total'] = df_transformado['precio_clp'] * df_transformado['stock']
    
    # Métrica B: Clasificación operativa según niveles de existencia
    def categorizar_stock(cantidad):
        if cantidad == 0:
            return 'AGOTADO'
        elif cantidad <= 5:
            return 'STOCK CRITICO'
        else:
            return 'STOCK SALUDABLE'
            
    df_transformado['segmento_disponibilidad'] = df_transformado['stock'].apply(categorizar_stock)
    
    print(f"  -> Transformacion finalizada con exito. Columnas actuales: {list(df_transformado.columns)}")
    return df_transformado