# VinylFlow: Pipeline Automatizado de DataOps para Inventario de Vinilos

Este proyecto implementa un pipeline de datos modular, contenerizado y automatizado bajo los principios de la cultura **DataOps** para la gestión, normalización y aseguramiento de la calidad del inventario de una distribuidora de música y discos de vinilo.

La solución aborda de forma resiliente problemáticas críticas de completitud y consistencia operativa en lotes masivos de datos (escalables a más de 500 registros), tales como la duplicidad de catálogos, registros con celdas vacías y anomalías semánticas de negocio (precios invertidos o valores de stock negativos).

## 📊 Arquitectura del Proyecto

El flujo de software sigue una estructura modular estricta para garantizar la mantenibilidad, aislamiento de responsabilidades y el desacoplamiento de las etapas del ciclo de vida del dato:

```text
├── data/
│   ├── vinilos.csv                 # Archivo fuente crudo en texto plano
│   └── dw_vinylflow.db             # Data Warehouse relacional de destino (SQLite)
├── data_quality/
│   └── validador.py                # Control de calidad, completitud y consistencia
├── ingestion/
│   └── ingesta.py                  # Extracción segura de archivos físicos del disco
├── logs/
│   ├── anomalias_artistas_faltantes.log # Trazas de registros con artista ausente
│   ├── anomalias_nulos_descartados.log  # Registros omitidos por ausencia de SKU o Precio
│   ├── anomalias_precios_corregidos.log # Historial de precios invertidos transformados
│   ├── anomalias_precios_descartados.log# Registros descartados por precio equivalente a cero
│   ├── anomalias_stock_corregidas.log   # Historial de registros con stock modificado
│   ├── anomalias_titulos_faltantes.log  # Trazas de registros con título ausente
│   └── ejecucion_pipeline_YYYYMMDD.log  # Historial técnico unificado con marcas de tiempo
├── procesamiento/
│   └── transformacion.py           # Limpieza básica, casting y feature engineering
├── Dockerfile                      # Definición de la imagen inmutable del entorno
├── pipeline.py                     # Orquestador principal y configurador de logging
└── requirements.txt                # Dependencias estrictas del proyecto