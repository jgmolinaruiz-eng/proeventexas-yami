"""
Meta Cloud API Provider para Agente Yami - Proeventexas
Variables requeridas:
  META_ACCESS_TOKEN, META_PHONE_NUMBER_ID, META_VERIFY_TOKEN
"""

import os
import logging
import httpx
from typing import Optional
from fastapi import Request
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)

META_API_VERSION = "v19.0"

class MetaProvider:

    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("META_PHONE_NUMBER_ID")
        self.verify_token = os.getenv("META_VERIFY_TOKEN", "proeventexas2024")
        self.messages_url = (
            f"https://graph.facebook.com/{META_API_VERSION}"
            f"/{self.phone_number_id}/messages"
        )
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        logger.info(f"MetaProvider listo | Phone ID: {self.phone_number_id}")

    async def validar_webhook(self, request: Request) -> Optional[str]:
        """Verificación GET del webhook requerida por Meta."""
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        if mode == "subscribe" and token == self.verify_token:
            logger.info("Webhook Meta verificado correctamente")
            return challenge

        logger.warning(f"Verificación fallida | token_recibido={token}")
        return None

    async def parsear_webhook(self, request: Request) -> Optional[list]:
        """Parsea el payload POST de Meta y retorna lista de mensajes."""
        try:
            data = await request.json()

            if data.get("object") != "whatsapp_business_account":
                return None

            entry = data.get("entry", [])
            if not entry:
                return None

            changes = entry[0].get("changes", [])
            if not changes:
                return None

            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            if not messages:
                return None

            msg = messages[0]
            if msg.get("type") != "text":
                logger.info(f"Mensaje tipo '{msg.get('type')}' ignorado")
                return None

            contacts = value.get("contacts", [])
            name = contacts[0].get("profile", {}).get("name", "") if contacts else ""

         

           from types import SimpleNamespace
            
            resultado = SimpleNamespace(
                es_propio=False,
                texto=message_text,
                from_number=sender_phone,
                message_id=message_id,
                name=contact_name,
                tipo="text",
            )

            logger.info(f"Mensaje de {sender_phone}: {message_text[:50]}")
            return [resultado]

        except Exception as e:
            logger.error(f"Error parseando webhook Meta: {e}")
            return None

    async def enviar_mensaje(self, to: str, message: str) -> bool:
        """Envía mensaje de texto via Meta Cloud API."""
        to_clean = to.replace("+", "").replace(" ", "").replace("-", "")

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_clean,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    self.messages_url,
                    headers=self.headers,
                    json=payload
                )
            if response.status_code == 200:
                logger.info(f"Mensaje enviado a {to_clean}")
                return True
            else:
                logger.error(f"Error Meta API: {response.status_code} | {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")
            return False
