# agent/tools.py — Herramientas del agente Yami
# Generado por AgentKit

"""
Herramientas específicas de Proeventexas.
Extienden las capacidades de Yami más allá de responder texto.
"""

import os
import yaml
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")


def cargar_info_negocio() -> dict:
    """Carga la información del negocio desde business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def obtener_horario() -> dict:
    """Retorna el horario de atención de Proeventexas."""
    info = cargar_info_negocio()
    return {
        "horario": info.get("negocio", {}).get("horario", "No disponible"),
        "esta_abierto": True,  # TODO: calcular según hora actual y horario
    }


def buscar_en_knowledge(consulta: str) -> str:
    """
    Busca información relevante en los archivos de /knowledge.
    Retorna el contenido más relevante encontrado.
    """
    resultados = []
    knowledge_dir = "knowledge"

    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."

    for archivo in os.listdir(knowledge_dir):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:500]}")
        except (UnicodeDecodeError, IOError):
            continue

    if resultados:
        return "\n---\n".join(resultados)
    return "No encontré información específica sobre eso en mis archivos."


def registrar_lead(telefono: str, nombre: str, ciudad: str, interes: str) -> dict:
    """
    Registra un lead de subdistribuidor potencial.
    En producción esto se conectaría a un CRM.
    """
    lead = {
        "telefono": telefono,
        "nombre": nombre,
        "ciudad": ciudad,
        "interes": interes,
        "fecha": datetime.now().isoformat(),
        "status": "nuevo",
    }
    logger.info(f"Nuevo lead registrado: {lead}")
    # TODO: Integrar con CRM o base de datos de leads
    return lead


def calificar_lead(telefono: str) -> str:
    """
    Califica un lead según su interacción.
    Retorna: 'caliente', 'tibio' o 'frio'.
    """
    # TODO: Implementar lógica de calificación basada en historial
    return "tibio"
