"""Sürümlü MITRE ATLAS tekniği kataloğu ve gerekçeli eşleme.

ATLAS eşlemesi bulgunun alanlarından türetilir; her eşleme gerekçe içerir.
Sıradan erişim kontrolü hatası, injection kanıtı yoksa etikete sokulmaz.
"""
from __future__ import annotations

from aegis.contracts.models import Finding, SecurityProperty, StrategyFamily

# ATLAS v2 teknik kimlikleri (kamuya açık numaralandırma; açıklamalar özet)
ATLAS_CATALOG: dict[str, dict[str, str]] = {
    "AML.T0051": {
        "name": "LLM Prompt Injection",
        "summary": "Prompt içine talimat gömerek model davranışını değiştirme.",
    },
    "AML.T0052": {
        "name": "LLM Jailbreak Injection",
        "summary": "Güvenlik kısıtlarını aşmak için jailbreak promptu enjekte etme.",
    },
    "AML.T0054": {
        "name": "LLM Interpretability Manipulation",
        "summary": "Model iç temsilini manipüle ederek istenen davranışı tetikleme.",
    },
    "AML.T0059": {
        "name": "Store Poisoning of RAG via Prompt Injection",
        "summary": "RAG deposuna gömülü talimatla dolaylı injection.",
    },
    "AML.T0043": {
        "name": "LLM Meta Model Injection",
        "summary": "Meta prompt veya sistem talimatının hedeflenmesi.",
    },
    "AML.T0040": {
        "name": "ML Model Inference API Access",
        "summary": "Model çıkarım API'sinin yetkisiz kullanımı.",
    },
    "AML.T0029": {
        "name": "Discover Sensitive Information in Model Output",
        "summary": "Model çıktısında hassas bilgi keşfi.",
    },
    "AML.T0030": {
        "name": "Recover Sensitive Information from Model Output",
        "summary": "Model çıktısından hassas bilgi çıkarma.",
    },
    "AML.T0036": {
        "name": "Exfiltration via ML Inference API",
        "summary": "Çıkarım API üzerinden veri sızdırma.",
    },
}

# Özellik/strateji → ATLAS tekniği gerekçeli eşleme tablosu
_MAPPING_RULES: list[dict] = [
    {
        "property": SecurityProperty.DATA_INSTRUCTION_SEPARATION.value,
        "family": StrategyFamily.INDIRECT_INJECTION.value,
        "technique": "AML.T0059",
        "justification": "Güvenilmeyen belge içine gömülmüş talimat uygulandı; RAG deposu üzerinden dolaylı injection.",
    },
    {
        "property": SecurityProperty.DATA_INSTRUCTION_SEPARATION.value,
        "family": StrategyFamily.DIRECT_INJECTION.value,
        "technique": "AML.T0051",
        "justification": "Kullanıcı girdisindeki talimat, veri/talimat ayrımı olmaksızın modeli yönlendirdi.",
    },
    {
        "property": SecurityProperty.TASK_CONSTRAINT.value,
        "family": StrategyFamily.DIRECT_INJECTION.value,
        "technique": "AML.T0052",
        "justification": "Görev kısıtı, doğrudan jailbreak tarzı talimatla aşıldı.",
    },
    {
        "property": SecurityProperty.TASK_CONSTRAINT.value,
        "family": StrategyFamily.MULTI_TURN_MANIPULATION.value,
        "technique": "AML.T0051",
        "justification": "Çok turlu konuşmada güven istismarıyla görev kısıtı devre dışı bırakıldı.",
    },
    {
        "property": SecurityProperty.TASK_CONSTRAINT.value,
        "family": StrategyFamily.ENCODING_EVASION.value,
        "technique": "AML.T0052",
        "justification": "Kodlanmış talimatla kısıt aşma girişimi görev sınırını hedefledi.",
    },
    {
        "property": SecurityProperty.SECRET_CONFIDENTIALITY.value,
        "family": StrategyFamily.TENANT_ISOLATION.value,
        "technique": "AML.T0030",
        "justification": "Kanarya sırrı model çıktısında ortaya çıktı; çıktıdan hassas bilgi kurtarma.",
    },
    {
        "property": SecurityProperty.TENANT_ISOLATION.value,
        "family": StrategyFamily.TENANT_ISOLATION.value,
        "technique": "AML.T0040",
        "justification": "Çıkarım API'si tenant sınırı olmaksızın başka tenant verisine erişti.",
    },
    {
        "property": SecurityProperty.TOOL_AUTHORIZATION.value,
        "family": StrategyFamily.INDIRECT_INJECTION.value,
        "technique": "AML.T0036",
        "justification": "Belge içi talimat, yetkisiz araç çağrısıyla veri sızdırmayı tetikledi.",
    },
    {
        "property": SecurityProperty.TOOL_AUTHORIZATION.value,
        "family": StrategyFamily.DIRECT_INJECTION.value,
        "technique": "AML.T0036",
        "justification": "Kullanıcı talimatıyla yetkisiz araç çağrısı yürütüldü (excessive agency).",
    },
    {
        "property": SecurityProperty.OUTPUT_INTEGRITY.value,
        "family": StrategyFamily.OUTPUT_SCHEMA_ABUSE.value,
        "technique": "AML.T0054",
        "justification": "Yapılandırılmış çıktı sözleşmesi bozuldu; çıktı bütünlüğü manipüle edildi.",
    },
]


def map_finding_to_atlas(
    violated_property: str, strategy_family: str, observed_effect: str
) -> list[dict[str, str]]:
    """Özellik + strateji ailesinden ATLAS tekniği üretir; gerekçesiz eşleme yok."""
    out: list[dict[str, str]] = []
    for rule in _MAPPING_RULES:
        if rule["property"] == violated_property and rule["family"] == strategy_family:
            tech = ATLAS_CATALOG[rule["technique"]]
            out.append(
                {
                    "technique_id": rule["technique"],
                    "name": tech["name"],
                    "justification": rule["justification"],
                }
            )
    if not out:
        # Injection kanıtı yoksa zorla ATLAS etiketi verilmez
        out.append(
            {
                "technique_id": "unmapped",
                "name": "No ATLAS mapping",
                "justification": (
                    "Bu bulgunun özellik/strateji bileşimi ATLAS tekniklerini doğrudan "
                    "karşılamıyor; injection kanıtı olmadan zorla eşlenmedi."
                ),
            }
        )
    return out
