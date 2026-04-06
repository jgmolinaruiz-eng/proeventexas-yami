import os

def obtener_proveedor():
    provider = os.getenv("WHATSAPP_PROVIDER", "whapi").lower()
    if provider == "meta":
        from agent.providers.meta import MetaProvider
        return MetaProvider()
    elif provider == "twilio":
        from agent.providers.twilio import TwilioProvider
        return TwilioProvider()
    else:
        from agent.providers.whapi import WhapiProvider
        return WhapiProvider()# agent/ — Paquete principal del agente WhatsApp
