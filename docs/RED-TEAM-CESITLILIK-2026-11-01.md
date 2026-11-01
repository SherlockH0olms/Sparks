# Red araçları ve saldırı çeşitliliği — 2026-11-01

Bu rapor ilk 1.722 kaynakl?k a?aman?n tarihsel kayd?d?r. G?ncel geni?leme ve do?rulama: [RED-TEAM-GENISLETME-2026-11-01.md](RED-TEAM-GENISLETME-2026-11-01.md).

AEGIS Red artık gerçek framework kaynaklarını araç çağrısıyla okuyabilir, yerel dönüşümleri çalıştırabilir ve dönüşümleri zincirleyebilir. Çeşitlilik yalnız sekiz aile adını değiştirmekle sağlanmıyor: kaynak metni, seçilen mekanizma ve çalıştırılan bileşen adayın kaydına bağlanıyor.

## Kurulan bileşenler

| Framework | Sürüm | Benzersiz kaynak metni | Çalışan dönüşüm seçeneği | Kullanılan bölüm |
|---|---|---:|---:|---|
| [PyRIT](https://github.com/microsoft/PyRIT) | 1.1.0 | 920 | 32 | Jailbreak/seed/converter/executor kaynakları, gerçek `convert_async` |
| [Garak](https://github.com/NVIDIA/garak) | 0.17.1 | 802 | 2 | Saldırı kaynakları, gerçek `Base64` ve `CharCode` buff'ları |
| [Promptfoo](https://github.com/promptfoo/promptfoo) | 0.125.1 | — | 11 | Public `redteam.Strategies.action` üzerinden yerel stratejiler |
| Toplam | | 1.722 | 45 | |

Kaynak metinleri SHA-256 ile küresel olarak tekilleştirildi. Aynı kodlamanın farklı framework uygulamaları ve parametrik kodlama seçenekleri dönüşüm sayısında ayrı sayılır. 1.722 kaynak, 1.722 bağımsız executable araç veya 1.722 başarılı saldırı anlamına gelmez. Paket lisansları ve mevcut upstream kaynak bilgileri katalogda korunur.

Frameworkler `.venv-redtools` ve `.runtime/redtools-node` içinde uygulamadan ayrı çalışır. Garak'ın tam scanner/provider/model bağımlılıkları kurulmadı; ilgili veri ve buff bileşenleri çalıştırıldı. Hedef üzerinde bağımsız framework ajanları veya görsel/ses saldırıları bu değişiklikte çalıştırılmadı. Yerel model indirilmedi.

## Red'e eklenen araçlar

- `list_attack_methods`: 30 mekanizma grubunu, kaynak sayılarını ve kurulmuş dönüşüm seçeneklerini listeler.
- `get_attack_method`: seçilen mekanizmanın gerçek upstream metinlerini tam olarak döndürür; başka örnekler sayfalanabilir.
- `search_attack_resources`, `get_attack_resource`: bütün kaynakları arama ve tam metin okuma.
- `transform_attack`: gerçek framework bileşenini JSON üzerinden çalıştırır.

Mevcut `inspect_target` ve `submit_attack` korunur; toplam yedi native function tool vardır. Modelin sağladığı kod, komut, dosya yolu veya URL çalıştırılmaz. Hedefin gerçek araç şemaları okunur; yabancı belgeler/oracle değerleri Red'e açılmaz.

Önerilen mekanizma, önceki denemelerde daha az kullanılan uygun yöntemlerden seçilir. Red önceki kendi payload'larını ve yöntem geçmişini görür. Örnekler: continuation/prefix, few-shot poisoning, kod/tablo nesting, roleplay/simulator, refusal suppression, context hijacking/overload, policy puppetry, gradual escalation, tool confused deputy, Unicode/kodlama ve structured output breakout. Bu gruplar AEGIS'in kaynak seçimi için tanımladığı mekanizmalardır; her biri ayrı bir upstream tarayıcı algoritması olduğu iddia edilmez.

`transform_attack` bir `insertion_token` üretir. Model bu işareti adayına koyar; sunucu gerçek çıktıyı karakterlerini değiştirmeden yerleştirir. İşaret başka bir dönüşümün `text` alanında da kullanılabilir. Böylece görünmez Unicode karakterlerini modelin yeniden yazması gerekmez. Boyut ve tur limitleri yerleştirmeden sonra doğrulanır. Native teslimde kullanılan dönüşüm çıktısı payload'da yoksa model araç geri bildirimiyle düzeltir.

`red_strategy` sunucu tarafından üretilir: yöntem, kaynak sürüm/lisans/hash bilgisi, gerçek araç çağrıları ve dönüşümün adayda aynen bulunup bulunmadığı kaydedilir. `applied` doğrudan metin dahil edilmesini gösterir; bir zincirin ara çıktısı sonraki dönüşümde kodlanmışsa bu alanın false olması mümkündür. Framework sonuçları kalıcı kayıttan replay edilir; aynı agent adımında tekrar API veya framework çağrısı yapılmaz.

JSON modunda kaynaklar sunucu tarafından prompt'a eklenir. Bu yol modelin native araç çağırdığı şeklinde raporlanmaz. `AEGIS_RED_MAX_AGENT_STEPS=0` ile varsayılan adım üst sınırı kaldırıldı; kampanya kontrolü ve tanımlanmış bütçe her adımda kontrol edilir.

## Doğrulama

- Backend: 56 test geçti; replay/accounting, yanlış araçlar/argümanlar, JSON fallback, üç turlu hücre, tam kaynak okuma, yöntem rotasyonu, gerçek üç framework smoke testi, eksik dönüşüm geri bildirimi, Unicode yerleştirme ve dönüşüm zinciri dahil.
- Frontend: production build ve TypeScript geçti.
- Gerçek uygulamada Playwright: 1.722 kaynak / 45 dönüşüm görünümü, 30 yöntemlik listenin açılması, sıfır browser runtime hatası.
- Ekran kaydı: `.runtime/red-library-ui.png`.

Canlı üretim deneyi iki tur × sekiz gerçek kampanya hücresi kullandı. İlk tur sonuçları ikinci turdaki yöntem seçimine verildi. Model FW-GLM-5.3, native araç modu; uygulama output-token ve çağrı süresi limitleri None. Tam adaylar ve araç konuşmaları `.runtime/live-red-diversity-final.json` içine kaydedildi; `complete=true`.

Nihai sonuç: **16/16 geçerli aday, 16/16 native teslim, 16/16 gerçek kaynak okuma ve hedef inceleme, 15 farklı seçilmiş yöntem**. 53 sağlayıcı çağrısı; ortalama aday üretimi 81,5 saniye; iki paralel worker ile toplam 674,3 saniye. Truncation gözlenmedi. Ana deneyde dört PyRIT dönüşüm çağrısı yapıldı; iki çıktı adayda doğrudan yer aldı. Diğer çağrılar alternatif dönüşüm denemeleriydi; kullanılmış gibi sayılmadı.

| Aile | İlk tur | İkinci tur |
|---|---|---|
| direct_injection | prefix_completion | refusal_suppression |
| indirect_injection | code_nesting | context_hijacking |
| authority_spoofing | research_authority | policy_puppetry |
| multi_turn_manipulation | emergency_pressure | simulator |
| encoding_evasion | encoded_extraction | invisible_instruction |
| tenant_probe | cross_tenant_reference | creative_extraction |
| tool_misuse | tool_confused_deputy | tool_argument_laundering |
| schema_abuse | prefix_completion | table_nesting |

Promptfoo Unicode düzeltmesinin canlı kanıtı `.runtime/live-red-promptfoo-final.json` içindedir: model `promptfoo:homoglyph` çağırdı, insertion_token ile çıktısını teslim etti, `applied=true`. Gerçek Garak Base64 kullanımının canlı kaydı `.runtime/live-red-garak-integration.json` içindedir. Bu deneyler Red üretimini doğrular; yerel hedef ve Judge çağrısı yapılmadığından hedef ASR'si ölçülmemiştir. Yöntem sayısı native `get_attack_method` kayıtlarından hesaplanır; ayrı bir semantik eşdeğerlik sınıflandırması değildir.

## Çalıştırma

```powershell
.\.venv-win\Scripts\python.exe scripts\setup_redteam_tools.py
.\.venv-win\Scripts\python.exe scripts\test_red_live.py --tool-mode native --rounds 2 --workers 2 --output .runtime\live-red-diversity-final.json
```

Kurulumlar zaten varsa `setup_redteam_tools.py --index-only` kataloğu yeniden oluşturur. `.runtime`, `.venv-redtools` ve `.env` Git'e alınmaz. Genel bakışta kütüphane, Kapsam ekranında gerçekleşen çeşitlilik, deneme ayrıntısında kaynak/dönüşüm kayıtları bulunur. Açık uygulama: http://127.0.0.1:3002.

Açık uygulama ana kütüphane, kaynak araçları ve birebir çıktı yerleştirme koduyla başarıyla başlatıldı; Playwright kontrolü bu gerçek süreçte yapıldı. Son eklenen dönüşüm zincirleme kodu diskte ve testleri geçmiş durumda. Bu son ekin çalışan sürece alınması için yeniden başlatma otomatik onay denetimince reddedildi: `approval required by policy, but AskForApproval::Granular.sandbox_approval is false`. Bu oturumda sandbox onayı kapalı olduğu için son yeniden başlatma gerçekleştirilemedi; zincirleme eki uygulamanın sonraki yeniden başlatmasında etkinleşir.
