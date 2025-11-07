# Utiliza una imagen base de Python ligera.
FROM python:3.10-slim

# Establece el directorio de trabajo dentro del contenedor.
WORKDIR /app

# Copia el archivo de requisitos e instala las dependencias primero.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de tu código (incluyendo app.py y los archivos .xlsx).
COPY . .

# Expón el puerto que Streamlit usa por defecto.
EXPOSE 8501

# Define el comando para ejecutar Streamlit cuando el contenedor inicie.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]