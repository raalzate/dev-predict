#!/bin/bash


CONTAINER_NAME="prosody-local"
DOMAIN="localhost"
PASSWORD="pass"

# Lista de nombres de usuario de los agentes (la parte antes del @).
AGENTS=("planner" "reasoner" "estimator" "researcher", "webagent")


# --- LÓGICA DEL SCRIPT ---
echo "--- Iniciando el registro de agentes para Prosody en el contenedor '$CONTAINER_NAME' ---"

# Verificar si el contenedor está en ejecución
if ! podman container exists "$CONTAINER_NAME" || [ "$(podman container inspect -f '{{.State.Running}}' "$CONTAINER_NAME")" != "true" ]; then
    echo "Error: El contenedor '$CONTAINER_NAME' no existe o no está en ejecución."
    echo "Por favor, verifica el nombre del contenedor y que esté iniciado."
    exit 1
fi

echo "Contenedor encontrado. Registrando agentes..."

# Iterar sobre la lista de agentes y registrarlos
for agent_user in "${AGENTS[@]}"; do
    echo "-> Registrando agente: ${agent_user}@${DOMAIN}"
    
    # Comando para ejecutar 'prosodyctl' dentro del contenedor de Podman
    #  podman exec prosody-local prosodyctl register "webagent" "localhost" "pass"
    podman exec "$CONTAINER_NAME" prosodyctl register "$agent_user" "$DOMAIN" "$PASSWORD"
    
    # Comprobar el código de salida del comando
    if [ $? -eq 0 ]; then
        echo "   Agente '${agent_user}' registrado exitosamente."
    else
        echo "   ¡Error! Hubo un problema al registrar al agente '${agent_user}'."
        echo "   Es posible que el usuario ya exista o haya un problema con Prosody."
    fi
done

echo "--- Proceso de registro completado. ---"
