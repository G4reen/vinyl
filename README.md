# VinylFlow: Pipeline Automatizado de DataOps para Inventario de Vinilos

Este proyecto implementa un pipeline de datos modular, contenerizado y automatizado bajo los principios de la cultura **DataOps** para la gestión, normalización y aseguramiento de la calidad del inventario global de una distribuidora de música y discos de vinilo.

La solución aborda problemáticas críticas de consistencia operativa, tales como la duplicidad de catálogos, registros con errores de formato y anomalías semánticas de negocio (precios inválidos o valores de stock negativos).

## 📊 Arquitectura del Proyecto

El flujo de software sigue una estructura puramente modular para garantizar la mantenibilidad, escalabilidad y el aislamiento de responsabilidades:

```text
├── data/
│   ├── vinilos.csv                 # BASE DE DATOS DE VINILOS
│   └── dw_vinylflow.db             # Data Warehouse relacional final (SQLite)
├── data_quality/
│   └── validador.py                # Validación estructural y semántica de negocio
├── ingestion/
│   └── ingesta.py                  # Extracción segura de archivos físicos del disco
├── logs/
│   ├── anomalias_precios_detectadas.log  # Registros aislados por fallas de precio
│   ├── anomalias_stock_corregidas.log    # Historial de registros con stock corregido
│   └── ejecucion_pipeline_YYYYMMDD.log   # Historial técnico con marcas de tiempo
├── procesamiento/
│   └── transformacion.py           # Limpieza, casting y feature engineering
├── Dockerfile                      # Definición de la imagen inmutable del entorno
├── pipeline.py                     # Orquestador principal del ciclo de vida del dato
└── requirements.txt                # Dependencias estrictas del proyecto