# Utiliza una imagen base de Python ligera.
FROM python:3.10-slim

# Establece el directorio de trabajo dentro del contenedor.
WORKDIR /app

# Copia el archivo de requisitos e instala las dependencias.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código (incluyendo app.py y los archivos .xlsx).
COPY . .

# Expón el puerto que Streamlit usa por defecto (opcional, pero ayuda a documentar).
EXPOSE 8080

# Define el comando para ejecutar Streamlit usando la variable de entorno PORT.
# Cloud Run inyecta la variable PORT, asegurando que Streamlit use el puerto 8080.
CMD ["streamlit", "run", "app.py", "--server.port", "8080", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false"]