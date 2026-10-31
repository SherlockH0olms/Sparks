"""Deneme zinciri yardımcıları: hedef çağrısının tek doğru biçimi.

Motor, bulgu doğrulama, Repair kapıları ve Verification süitleri hep aynı
şekilde hedefe deneme göndermelidir: turlar sırayla, her yanıt bir sonraki
turun konuşma geçmişine eklenir. Bu modül o tek biçimi sağlar; `turns[0]`
kısayolu (çok turlu zincirin sessizce atılması) her yerde yasaklanır.
"""
from __future__ import annotations

from aegis.targets.synthetic_assistant.app import (
    AssistantRequest,
    AssistantResponse,
    SyntheticAssistant,
)


def run_attempt_chain(
    assistant: SyntheticAssistant,
    turns: list[str],
    tenant_context,
    document_ids: list[str] | None = None,
    expect_json: bool = False,
) -> AssistantResponse:
    """Turları sırayla gönder; son turun yanıtını döndür.

    history: her turda bir önceki kullanıcı mesajı + asistan yanıtı birikir.
    Tek turlu denemelerde davranış tek mesajla aynıdır.
    """
    history: list[dict[str, str]] = []
    resp = None
    for i, turn_text in enumerate(turns):
        req = AssistantRequest(
            message=turn_text,
            tenant_context=tenant_context,
            assigned_document_ids=document_ids or [],
            expect_json=expect_json,
            history=history,
        )
        resp = assistant.handle(req)
        if i < len(turns) - 1:
            history.append({"role": "user", "content": turn_text})
            history.append({"role": "assistant", "content": resp.text[:400]})
    if resp is None:
        # turns boş: boş mesaj gönder (değerlendirme zaten geçersiz işaretler)
        req = AssistantRequest(
            message="",
            tenant_context=tenant_context,
            assigned_document_ids=document_ids or [],
            expect_json=expect_json,
        )
        resp = assistant.handle(req)
    return resp


def documents_for_attempt(assistant: SyntheticAssistant, document_ids: list[str]) -> None:
    """Denemenin belge kimliklerinin asistan envanterinde olmasını sağla.

    Repair/Verification asistanları manifest belgeleriyle kurulur; Red'in
    atadığı test belgesi (doc_red_injected_*) yalnız keşif asistanında var.
    Kapılar ve süitler aynı belgeyle çalışmazsa güvenlik ön testi gerçek
    koşulu temsil etmez. Bu yardımcı eksik belgeleri sessizce ekler.
    """
    for doc_id in document_ids:
        if doc_id and doc_id not in assistant.documents:
            # belge gövdesi bilinmiyorsa boş referans eklemek yanıltıcıdır;
            # bilinen adlandırılmış Red belgeleri için gövde kütüphaneden alınır
            from aegis.red.library import injected_doc_body_for

            for lang in ("tr", "az", "en"):
                if doc_id == f"doc_red_injected_{lang}":
                    from aegis.contracts.models import DocumentRef

                    assistant.documents[doc_id] = DocumentRef(
                        doc_id=doc_id,
                        tenant="tenant-alpha",
                        title="Vendor Contract Draft (assigned)",
                        body=injected_doc_body_for(lang),
                        assigned_to="red",
                    )
                    break
