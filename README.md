# AEGIS LOOP

**Birleşik AI Red Teaming & Remediation Platformu**

> Tek platform: kapsam güdümlü keşif, yeniden üretilebilir bulgu, kontrollü düzeltme deneyi
> ve bağımsız doğrulama. Her karar sürüme, bütçeye ve kanıta bağlı.

Mövzu 10 (AI modellerinin güvenliği ve AI Red Teaming) için geliştirilmiştir.
MVP sınırı değil, genişleyebilir motor üzerinde uçtan uca doğrulanmış bir
deney ve kanıt altyapısı hedeflenmiştir.

> 📘 **Teknik referans:** [HANDBOOK.md](HANDBOOK.md) — mimari, sözleşmeler, durum
> makineleri, kapılar, API, DoD ve sınırlamalar; her madde kod karşılığı ve test
> kanıtıyla.

---

## Hızlı başlangıç

```bash
./run.sh                # backend (8000) + frontend (3000) tek komutla
```

veya ayrı ayrı:

```bash
# Backend
cd backend
PYTHONPATH=. ../.venv/bin/python -m uvicorn aegis.api:app --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Demo pipeline (UI'sız, uçtan uca akış + rapor)
cd backend && ../.venv/bin/python scripts/demo_pipeline.py

# Testler
cd backend && ../.venv/bin/python -m pytest
```

---

## Mimari

```text
                WEB PLATFORM (Next.js)
    Overview · Target · Campaign · Coverage · Findings
    Repair Lab · Verification · Report · Audit
                        │
                        ▼
                 CONTROL API (FastAPI)
     Kimlik · Yetki · İdempotency · Bütçe · Kill switch
                        │
                        ▼
              CAMPAIGN CONTROLLER (engine.py)
        Sürümlü durum makinesi + bütçe defteri + SSE
                        │
        ┌───────────────┼──────────────────┐
        ▼               ▼                  ▼
     RED LAB        REPAIR LAB       VERIFICATION LAB
   strateji küt.    kontrol kataloğu  bağımsız oracle
   kapsam ızg.      A/B/C/D adayları  replay/holdout
   hafıza + sched.  kapılar + diff    adaptive + utility
        │               │                  │
        └───────────────┼──────────────────┘
                        ▼
            ORTAK KANIT ALTYAPISI (contracts)
   Attempt · Assessment · Finding · EvidencePack · Budget
                        │
                        ▼
               TARGET ADAPTER (sentetik hedef)
      2-tenant RAG asistanı · simüle LLM · araçlar
```

## Temel tasarım ilkeleri (kodda karşılığı olan)

| İlke | Karşılığı |
|---|---|
| execution_status ≠ verdict | `Attempt.execution_status` / `Attempt.verdict` ayrı alanlar; timeout saldırı engellendi demek değildir |
| Red, oracle sırlarına erişemez | `OracleVault` rol bazlı; `secrets_for_evaluator` yalnız evaluator_service |
| Modelin "gönderdim" demesi kanıt değildir | Değerlendirici yalnız deterministik kanıt kabul eder (tool log, retrieval log, kanarya) |
| Girdide zaten varsa sızıntı değildir | `vault.check_leak(..., inputs=...)` girdi temizliği yapar |
| Kapsam paydası görünür | `CoverageGrid.coverage_metrics()` — "uygulanamaz" hücre "geçti" sayılmaz |
| Scheduler gerekçeli | Her seçimde yapılandırılmış karar kaydı (SSE'de görünür) |
| Devam eden kampanyanın hedefi değişmez | Repair adayları baseline'ın izole kopyalarında (`SyntheticAssistant(documents, defense)`) |
| Final doğrulama rezervi korunur | `BudgetLedger.reserve("final_verification_reserve")` |
| COMPLETED = akış bitti, "güvenli" değil | Durum makinesi yorum taşımaz; rapor açıkça yazar |
| Uydurma demo yüzdeleri yok | Ölçüm olmayan hücrede UI "—" gösterir |
| Metin varyasyonu ≠ ayrı açık | Gruplama: özellik + sınır + bileşen + etki bazlı |
| ATLAS eşlemesi gerekçelidir | `findings/atlas.py` — injection kanıtı yoksa zorla eşleme yok |

## Hackathon gereksinimleri karşılığı

| Gereksinim | Platformdaki karşılığı | Kanıt |
|---|---|---|
| Hedef model | Sentetik 2-tenant RAG asistan (sürümlü) | `targets/synthetic_assistant` |
| 2–3 saldırı | 8 strateji × 3 dil × 6 özellik = 33 kapsam hücresi | `red/library.py` |
| Nicel dayanıklılık | Kapsam %, ASR, tekrar üretim, utility, gecikme, bütçe | `coverage`, `verification` |
| MITRE ATLAS | Sürümlü katalog + gerekçeli eşleme | `findings/atlas.py` |
| Savunma gösterimi | A/B/C/D aday karşılaştırması + kapılar | `repair/lab.py` |
| Otomatik rapor | Markdown + HTML + EvidencePack | `reporting/report.py` |

## Demo akışı (jüri için)

1. **Overview** — hedef ve sürüm görünür; "+ Yeni Kampanya" ile başlat
2. **Campaign Console** — scheduler'ın seçim gerekçeleri canlı (SSE)
3. **Coverage** — uygulanamaz hücreler dâhil kapsam haritası
4. **Findings** — gruplanmış bulgular; detayda kanıt, tekrar, küçültme, ATLAS
5. **Repair Lab** — A/B/C/D karşılaştırması; B adayının gerçek ret gerekçesi
6. **Verification** — 4 bağımsız süit (replay/unseen/adaptive/utility)
7. **Report** — önce/sonra; HTML indirilebilir
8. **Audit** — denetim kaydı + kill switch

## Testler

```bash
cd backend && ../.venv/bin/python -m pytest   # 14 test
```

Kapsam: durum makinesi, vault izolasyonu, timeout/verdict ayrımı, saldırı
üretimi, savunma doğrulaması, utility korunumu, deterministik tekrar, ATLAS
gerekçesi, uçtan uca kampanya.

## Sınırlamalar (dürüstçe)

- Hedef **simüle** bir LLM uygulamasıdır; gerçek model davranış dağılımı temsil edilmez.
- Belgular tanımlı kapsam, erişim profili ve sürüm kümesine bağlıdır.
- Injection desen filtresi kodlama/parafraz ile aşılabildiği için tek başına
  güvenlik kontrolü olarak önerilmez (platform bunu da ölçer ve raporlar).
- Bellek içi durum: yeniden başlatmada kampanyalar sıfırlanır (hakaton kapsamı).
