"""Sentetik hedef: iki tenant'lı belge asistanı.

Bu hedef, bir LLM uygulamasının tipik bileşenlerini (retrieval, prompt
birleştirme, çıktı şeması, araç çağrısı) **deterministik ve izlenebilir**
biçimde simüle eder. Amaç gerçek davranış aralığını kapsamak değil;
platformun deney ve kanıt altyapısını gerçekçi bir hedef üzerinde
göstermektir.

Bilinçli tasarım kusurları (vulnerable-by-design):
    * retrieval tenant filtresini atlayabilir (rev1'de yok)
    * sistem promptu belge içeriğiyle birleştirilir (instruction/data ayrımı yok)
    * model çıktısı şemaya göre doğrulanmaz
    * araç çağrıları hedef uygulama içinde yetkilendirilmez
"""
from aegis.targets.synthetic_assistant.manifest import build_manifest
from aegis.targets.synthetic_assistant.app import (
    SyntheticAssistant,
    AssistantRequest,
    AssistantResponse,
    RetrievalMode,
)

__all__ = [
    "build_manifest",
    "SyntheticAssistant",
    "AssistantRequest",
    "AssistantResponse",
    "RetrievalMode",
]
