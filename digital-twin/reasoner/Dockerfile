# Imagen base liviana con Python 3.11
FROM python:3.11-slim

# Evita buffering y bytecode innecesario
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Crea el directorio de trabajo
WORKDIR /app

# Copia primero el requirements.txt para aprovechar la cache
COPY requirements.txt .

# Instala dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código del proyecto
COPY . .

# Establece el PYTHONPATH (importaciones absolutas más limpias)
ENV PYTHONPATH=/app

# Exponer el puerto XMPP (opcional)
EXPOSE 5222

# Comando por defecto (puedes reemplazarlo en docker-compose)
CMD ["python", "-m", "reasoner_agent"]
