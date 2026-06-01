# 1. Imagen base oficial de Python ligera
FROM python:3.10-slim

# 2. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar primero el archivo de requerimientos para aprovechar la caché de Docker
COPY requirements.txt .

# 4. Instalar las dependencias del proyecto
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar todas las carpetas y archivos de tu proyecto al contenedor
COPY . .

# 6. Comando por defecto que ejecuta el orquestador principal al iniciar el contenedor
CMD ["python", "pipeline.py"]