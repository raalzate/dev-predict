# Gemelo Digital de Estimación de Proyectos de Software

Este proyecto implementa un sistema multiagente inteligente para automatizar la estimación de tareas de desarrollo de software. Utiliza una combinación de Machine Learning, un Agente Investigador web y un Modelo de Lenguaje Grande (LLM) para analizar historias de usuario y producir estimaciones refinadas de esfuerzo, tiempo y complejidad.

---

## 🏛️ Arquitectura

El sistema se basa en una arquitectura de **microservicios cognitivos** utilizando la plataforma de agentes **SPADE**. Cada agente es un especialista autónomo que colabora a través de un bus de mensajes asíncrono (XMPP).

**Flujo de Estimación:**
```

Entrada (Historias de Usuario)
↓

1.  📋 Agente Planificador (Orquesta el lote)
    ↓
2.  🧠 Agente Razonador (Inicia el proceso para una historia)
    ↓         ↘
    ↓           ↘
3.  📈 Agente Estimador (Da una estimación base con ML)      4. 🌐 Agente Investigador (Busca contexto en la web)
    ↓           ↙
    ↓         ↙
4.  🧠 Agente Razonador (Sintetiza la información)
    ↓
5.  💡 Google Gemini (Refina la estimación y justifica)
    ↓
6.  📋 Agente Planificador (Recopila el resultado)
    ↓
    Salida (Informe Final)

````

---

## ✨ Características Principales

* **Sistema Multiagente Colaborativo:** Cuatro agentes especializados que trabajan juntos.
* **Estimación Basada en Datos:** Utiliza un modelo de Machine Learning (`GradientBoostingRegressor`) entrenado con datos históricos.
* **Contexto en Tiempo Real:** El `Agente Investigador` busca en la web para enriquecer las estimaciones con información técnica actualizada.
* **Razonamiento Avanzado:** El `Agente Razonador` integra toda la información y utiliza la **API de Google Gemini** para un análisis y justificación de nivel experto.
* **Configuración Flexible:** Permite definir el stack tecnológico del proyecto (`tech_stack.json`) para refinar las búsquedas.

---

## 🚀 Puesta en Marcha

Sigue estos pasos para configurar y ejecutar el proyecto en tu entorno local.

### 1. Prerrequisitos
* Python 3.9+
* Docker (o Podman)
* Una clave de API de Google Gemini

### 2. Guía de Instalación

1.  **Clonar el Repositorio**
    ```bash
    git clone <url_del_repositorio>
    cd <nombre_del_repositorio>
    ```

2.  **Configurar el Entorno Virtual e Instalar Dependencias**
    ```bash
    python -m venv spade_env
    source spade_env/bin/activate
    pip install -r proyect/requirements.txt
    ```

3.  **Iniciar el Servidor XMPP (Prosody)**
    Ejecuta el siguiente comando para iniciar el servidor de mensajería en un contenedor Docker. Asegúrate de tener la carpeta `prosody-config` con el archivo `prosody.cfg.lua`.
    ```bash
    docker run -d --name prosody -p 5222:5222 -v $(pwd)/prosody-config:/etc/prosody prosody/prosody
    ```

4.  **Registrar los Agentes**
    Ejecuta el script para crear las cuentas de los agentes en el servidor Prosody.
    ```bash
    chmod +x register_agents.sh
    ./register_agents.sh
    ```

5.  **Configurar la API Key de Gemini**
    -   Renombra el archivo `.env.example` a `.env`.
    -   Abre el archivo `.env` y pega tu clave de API.
    ```
    GEMINI_API_KEY="TU_API_KEY_DE_GEMINI_AQUI"
    ```

6.  **Entrenar el Modelo de Machine Learning**
    Este paso lee el `stories_dataset.csv`, entrena el modelo y crea los archivos `effort_model.pkl` y `text_vectorizer.pkl`.
    ```bash
    # Desde la carpeta raíz del proyecto
    python proyect/train_model.py 
    ```
    
### 3. Ejecución del Sistema

Una vez completada la configuración, lanza el sistema multiagente desde la carpeta `digital-twin`.


```bash
cd digital-twin
python main.py
````

El sistema comenzará a procesar el lote de historias definido en `stories_batch.json` y mostrará el informe final en la consola.

