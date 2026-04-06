"""
Proveedor Meta Cloud API para el Agente Yami de Proeventexas
=====================================================================
Implementa la interfaz base del patrón adaptador de AgentKit.
Métodos requeridos:
  - parsear_webhook(data)  → dict con {from, message, message_id} o None
  - enviar_mensaje(to, message) → bool

Variables de entorno requeridas:
  - META_ACCESS_TOKEN       (token permanente de Meta Business)
  - META_PHONE_NUMBER_ID    (ID del número: 1079814968545925)
  - META_VERIFY_TOKEN       (token de verificación webhook: proeventexas2024)
"""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

# Versión de la Graph API de Meta (estable a 2025)
META_API_VERSION = "v19.0"
META_API_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"


class MetaProvider:
    """
    Adaptador para Meta Cloud API (WhatsApp Business Platform).
    Implementa la misma interfaz que whapi.py para intercambiabilidad.
    """

    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("META_PHONE_NUMBER_ID")
        self.verify_token = os.getenv("META_VERIFY_TOKEN", "proeventexas2024")

        if not self.access_token:
            raise ValueError("META_ACCESS_TOKEN no está configurado en las variables de entorno")
        if not self.phone_number_id:
            raise ValueError("META_PHONE_NUMBER_ID no está configurado en las variables de entorno")

        self.messages_url = f"{META_API_BASE_URL}/{self.phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        logger.info(f"MetaProvider inicializado | Phone Number ID: {self.phone_number_id}")

    # ------------------------------------------------------------------
    # VERIFICACIÓN DEL WEBHOOK (GET)
    # Meta envía esto cuando configuras el webhook en el Developer Portal
    # ------------------------------------------------------------------

    def verificar_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verifica la autenticidad del webhook con Meta.
        Retorna el challenge si la verificación es exitosa, None si falla.

        Uso en main.py:
            @app.get("/webhook")
            async def webhook_get(hub_mode, hub_verify_token, hub_challenge):
                result = proveedor.verificar_webhook(hub_mode, hub_verify_token, hub_challenge)
                if result:
                    return PlainTextResponse(result)
                raise HTTPException(status_code=403)
        """
        if mode == "subscribe" and token == self.verify_token:
            logger.info("Webhook de Meta verificado correctamente")
            return challenge
        logger.warning(f"Verificación fallida | mode={mode} | token_recibido={token}")
        return None

    # ------------------------------------------------------------------
    # PARSEAR WEBHOOK (POST) — extrae el mensaje del cliente
    # ------------------------------------------------------------------

    def parsear_webhook(self, data: dict) -> Optional[dict]:
        """
        Parsea el payload JSON que Meta envía al webhook.
        Retorna un dict normalizado o None si no hay mensaje de texto válido.

        Formato de retorno (compatible con toda la cadena de AgentKit):
        {
            "from":       "15551234567",   # número sin + ni espacios
            "message":    "Hola, ¿cuánto cuesta el tinte?",
            "message_id": "wamid.HBgN...", # ID único del mensaje
            "name":       "María López"    # nombre del contacto (opcional)
        }
        """
        try:
            # Validar estructura raíz
            if data.get("object") != "whatsapp_business_account":
                logger.debug("Webhook ignorado: object no es whatsapp_business_account")
                return None

            # Navegar hasta el mensaje
            entry = data.get("entry", [])
            if not entry:
                return None

            changes = entry[0].get("changes", [])
            if not changes:
                return None

            value = changes[0].get("value", {})

            # Verificar que hay mensajes (no solo status updates)
            messages = value.get("messages", [])
            if not messages:
                logger.debug("Webhook recibido pero sin mensajes (probablemente status update)")
                return None

            msg = messages[0]

            # Solo procesar mensajes de texto (ignorar audio, imagen, etc.)
            msg_type = msg.get("type")
            if msg_type != "text":
                logger.info(f"Mensaje de tipo '{msg_type}' recibido — solo se procesan mensajes de texto")
                return None

            # Extraer campos
            sender_phone = msg.get("from", "")
            message_id = msg.get("id", "")
            message_text = msg.get("text", {}).get("body", "").strip()

            if not message_text:
                return None

            # Nombre del contacto (si está disponible)
            contacts = value.get("contacts", [])
            contact_name = ""
            if contacts:
                contact_name = contacts[0].get("profile", {}).get("name", "")

            logger.info(f"Mensaje recibido | De: {sender_phone} | Texto: {message_text[:60]}...")

            return {
                "from": sender_phone,
                "message": message_text,
                "message_id": message_id,
                "name": contact_name,
            }

        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error al parsear webhook de Meta: {e} | Payload: {data}")
            return None

    # ------------------------------------------------------------------
    # ENVIAR MENSAJE — responde al cliente
    # ------------------------------------------------------------------

    def enviar_mensaje(self, to: str, message: str) -> bool:
        """
        Envía un mensaje de texto al número especificado via Meta Cloud API.

        Args:
            to:      Número de teléfono destino (ej: "15551234567")
            message: Texto a enviar (máx 4096 caracteres)

        Returns:
            True si el mensaje se envió correctamente, False si hubo error.
        """
        # Meta requiere el número sin + pero con código de país
        to_clean = to.replace("+", "").replace(" ", "").replace("-", "")

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_clean,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message,
            },
        }

        try:
            response = requests.post(
                self.messages_url,
                headers=self.headers,
                json=payload,
                timeout=15,
            )

            if response.status_code == 200:
                response_data = response.json()
                msg_id = response_data.get("messages", [{}])[0].get("id", "")
                logger.info(f"Mensaje enviado correctamente | Para: {to_clean} | ID: {msg_id}")
                return True
            else:
                logger.error(
                    f"Error enviando mensaje | Status: {response.status_code} | "
                    f"Respuesta: {response.text}"
                )
                return False

        except requests.exceptions.Timeout:
            logger.error(f"Timeout al enviar mensaje a {to_clean}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red al enviar mensaje a {to_clean}: {e}")
            return False

    # ------------------------------------------------------------------
    # MARCAR MENSAJE COMO LEÍDO (opcional pero recomendado)
    # ------------------------------------------------------------------

    def marcar_leido(self, message_id: str) -> bool:
        """
        Marca un mensaje como leído (muestra palomitas azules en WhatsApp).
        Opcional — mejora la experiencia del usuario.
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        try:
            response = requests.post(
                self.messages_url,
                headers=self.headers,
                json=payload,
                timeout=10,
            )
            if response.status_code == 200:
                logger.debug(f"Mensaje {message_id} marcado como leído")
                return True
            return False
        except requests.exceptions.RequestException as e:
            logger.debug(f"No se pudo marcar como leído: {e}")
            return False
