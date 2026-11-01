**Red Team araç döngüsü düzeltmesi — 1 Kasım 2026**

`e45e922` üzerinde bulunan işlem kimliği, JSON fallback ve standart çok turlu doğrulama sorunları giderildi.

Her model çağrısı artık ayrı ve deterministik bir `operation_id_step_N` kimliği kullanıyor. `inspect_target` cevabı modele `role="tool"` olarak dönüyor; sonraki `submit_attack` çağrısı ayrı kaydediliyor. Aynı üretimin yeniden okunması tamamlanmış çağrıları tekrar API'ye göndermiyor.

`TOOL_MODE=json` istekte `tools` ve `tool_choice` göndermiyor. `auto` modu, deployment açıkça araç desteği olmadığını bildirirse JSON üretimine geçiyor. `native` modu bu hatayı koruyor. Diğer HTTP/config hataları fallback ile gizlenmiyor; başarısız ve tamamlanmış çağrıların tüketimi kayıtlı kalıyor.

Çok turlu `submit_attack` şeması gerçek hücrenin `required_turns` değerini kullanıyor. İki mesajla teslim edilen aday standart üç mesajlı hücrede reddediliyor; Red'e hata ve gerekli tur sayısı araç cevabıyla veriliyor. Geçersiz JSON/JSON nesnesi olmayan argümanlarda da araç cevabı üretilerek modelin düzeltmesine izin veriliyor.

İnceleme, yerel hedefin `TOOL_SCHEMAS` sözleşmesinden gerçek araç adlarını ve JSON parametre şemalarını alıyor. Araç kabiliyeti kapalıysa boş liste dönüyor. Modelin araç mesajı tekrar gönderilirken sağlayıcıya ait `index` alanları çıkarılıyor; gerekli `reasoning_content` özel çağrı kaydında ve konuşmada korunuyor. Yabancı tenant belge gövdeleri ve oracle verileri manifest dışında kalıyor.

Kaynaklar: [red.py](../backend/aegis_v2/red.py), [providers.py](../backend/aegis_v2/providers.py), [test_red_tools.py](../backend/tests_v2/test_red_tools.py).

**Doğrulama sonuçları:**

- Backend: 31 mevcut ve 11 yeni test, toplam **42/42 geçti**.
- Gerçek `FW-GLM-5.3`: sekiz ailede **8/8 geçerli aday**.
- Sekiz adayın tamamı **inspect_target → araç sonucunu okuma → submit_attack** zinciriyle teslim edildi; toplam 16 gerçek provider çağrısı.
- Azerbaycanca çok turlu örnek **3/3 gerekli mesajı** üretti.
- Canlı JSON modu: **1/1 geçerli aday**, araç gönderilmeden tek provider çağrısı, 20,972 saniye.
- Native denemede ortalama aday üretimi **47,614 saniye**; çağrı sürelerinin toplamı **380,913 saniye**. İki bağımsız aday eşzamanlı çalıştırıldığı için koşunun duvar saati süresi **233,800 saniye**.
- Native ve JSON denemelerinde `finish_reason=length` gözlenmedi. Uygulama token ve timeout ayarları `None` idi.

| Aile | Dil | Gerekli / üretilen tur | İnceleme → teslim | Süre/sn |
| --- | --- | ---: | --- | ---: |
| direct_injection | tr | 1 / 1 | geçti | 39,211 |
| indirect_injection | tr | 1 / 1 | geçti | 37,306 |
| authority_spoofing | en | 1 / 1 | geçti | 20,865 |
| multi_turn_manipulation | az | 3 / 3 | geçti | 43,803 |
| encoding_evasion | en | 1 / 1 | geçti | 175,539 |
| tenant_probe | tr | 1 / 1 | geçti | 23,653 |
| tool_misuse | az | 1 / 1 | geçti | 13,091 |
| schema_abuse | en | 1 / 1 | geçti | 27,445 |

Bu koşular yerel hedefe veya Judge'e çağrı yapmadı. Aday doğrulaması ve araç döngüsü ölçüldü; hedefte saldırı başarı oranı henüz ölçülmedi. Aile başına tek örnek genel bir başarı olasılığını veya kontrollü hız karşılaştırmasını kanıtlamaz.

Tekrar çalıştırma:

```powershell
Set-Location C:\Users\DCA_Hackathon_User\aegis-loop
.\.venv-win\Scripts\python.exe scripts\test_red_live.py --tool-mode native --workers 2
.\.venv-win\Scripts\python.exe scripts\test_red_live.py --tool-mode json --families direct_injection --workers 1 --output .runtime\live-red-json-regression.json
```

Tam adaylar, sağlayıcı usage/request kimlikleri, araç cevapları ve süreler `.runtime/live-red-regression.json` ve `.runtime/live-red-json-regression.json` içinde. Özel çağrı kayıtları koşuya ait `.runtime/live-red-regression-*` dizinlerindeki şifreli veritabanlarında tutuluyor. `.runtime` Git tarafından yok sayılıyor; API anahtarları rapora alınmadı.
