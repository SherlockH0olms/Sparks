"""AEGIS LOOP — Birleşik AI Red Teaming & Remediation Platformu.

Katmanlar:
    contracts  — ortak veri sözleşmeleri (TargetManifest, Attempt, Finding, ...)
    core       — durum makineleri, bütçe defteri, olay veriyolu, kimlik
    coverage   — kapsam hücreleri, uygulanabilirlik, scheduler
    red        — strateji kütüphanesi, hafıza, aday üretimi
    evaluation — oracle vault, bağımsız değerlendirme, verdict mantığı
    findings   — doğrulama, küçültme, gruplama, ATLAS eşleme
    repair     — kontrol kataloğu, adaylar, kapılar, karşılaştırma
    verification — bağımsız final süitleri ve metrikler
    reporting  — EvidencePack ve rapor üretimi
    api        — FastAPI uygulaması (Control API)
"""

__version__ = "1.0.0"
