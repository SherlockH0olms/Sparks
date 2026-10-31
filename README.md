# AEGIS LOOP v2

İzinli AI sistemleri için kapsamlı keşif, kanıt, yapılandırma düzeltmesi ve bağımsız doğrulama platformu.

**Güncel kod:** `backend/aegis_v2`. Eski `aegis.api` komutları kullanılmaz. Mimari tasarım için HANDBOOK.md; çalıştırma ve doğrulanmış durum için [docs/TESLIM-2026-10-31.md](docs/TESLIM-2026-10-31.md).

## Windows'ta başlatma

```powershell
cd C:\Users\DCA_Hackathon_User\aegis-loop
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -Mode production -ApiPort 8002 -WebPort 3002 -Open
```

Varsayılan portlar 3000/8000; başka uygulama kullanıyorsa yukarıdaki 3002/8002 seçimi çalışır. `-Mode dev` geliştirme sunucusunu açar. Ctrl+C iki sunucuyu kapatır.

## API anahtarları

Proje kökündeki `.env` dosyasına yazılır; dosya Git'e alınmaz.

| Değişken | Kullanım |
|---|---|
| `AEGIS_ADMIN_TOKEN` | Uygulamaya giriş. Boşsa başlatıcı güçlü, rastgele bir değer üretir. |
| `AEGIS_RED_ENDPOINT`, `AEGIS_RED_API_KEY`, `AEGIS_RED_MODEL` | Saldırı üreticisi. |
| `AEGIS_JUDGE_ENDPOINT`, `AEGIS_JUDGE_API_KEY`, `AEGIS_JUDGE_MODEL` | Bağımsız semantik değerlendirici. |
| `AEGIS_LOCAL_ENDPOINT`, `AEGIS_LOCAL_MODEL`, `AEGIS_LOCAL_API_KEY` | Test edilecek yerel hedef; kimlik doğrulama istemiyorsa son alan boş kalır. |

Foundry `/models` ve `/openai/v1` adresleri desteklenir. `/openai/v1` için `AEGIS_RED_PROVIDER=foundry` / `AEGIS_JUDGE_PROVIDER=foundry` kullanılır; API sürüm parametresi eklenmez. Azure OpenAI'nin eski deployment API'si için provider `azure_openai` ve ilgili `*_DEPLOYMENT` alanları gerekir. Sunucuyu `.env` değişikliğinden sonra yeniden başlatın.

```powershell
.\.venv-win\Scripts\python.exe scripts\setup.py --check-providers
```

Bu komut Red ve Judge'a birer kısa bağlantı isteği gönderir. Anahtarları ve yanıt gövdelerini loglamaz. Yerel modeliniz hazır olduğunda Hedefler ekranında modelin gerçek revision'ını girip bağlantıyı test edin.

## Açıkça etiketlenen anahtarsız demo

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -Mode demo -ApiPort 8003 -WebPort 3003 -Open
```

Giriş: `aegis-offline-demo-access-key-2026-only`.

Bu ayrı SQLite veritabanında açık **TEST FIXTURE ORTAMI** etiketiyle çalışır. Gerçek Foundry/Judge/yerel model çağrısı yapılmaz; bir bağlantı hatasında otomatik devreye girmez. Araç yetkisi, tenant izolasyonu ve çıktı şeması için 9 TR/AZ/EN kapsam hücresi, 3 bulgu, A/B/C/D deneyleri, 4 final süiti ve rapor üretir. Gerçek ve demo tarayıcı oturumlarını ayrı tutmak için gerçek adresi `127.0.0.1:3002`, demoyu `localhost:3003` ile açabilirsiniz.

## Doğrulama

```powershell
cd backend
..\.venv-win\Scripts\python.exe -m pytest --basetemp=..\.runtime\pytest-manual
cd ..\frontend
npm.cmd run build
# Demo 3003/8003 üzerinde açıkken:
$env:AEGIS_E2E_REUSE='true'
npm.cmd run test:e2e
```

Linux/macOS: `./run.sh --mode production`. İlk çalıştırma Python sanal ortamını ve npm bağımlılıklarını kurar. GitHub Actions backend, build ve Chromium tarayıcı kontrollerini yürütür.

## Mimari ve sınırlar

- FastAPI + Pydantic sözleşmeleri; SQLite/PostgreSQL üzerinde kalıcı kampanya, lease, checkpoint, SSE ve audit.
- Foundry/Azure/OpenAI uyumlu Red ve Judge; bağımsız yerel OpenAI uyumlu hedef, sürümlü RAG ve yan etkisiz mock araçlar.
- TR/AZ/EN kapsam hücreleri; bütçeli üretim, yeniden üretim, tur azaltma ve bulgu gruplama.
- İzinli yapılandırma yamaları, hash/diff/rollback, model smoke testi, güvenlik ve pozitif utility kapıları.
- Dondurulmuş aday üzerinde replay, görülmemiş örnek, adaptif yeniden saldırı ve normal kullanım; boş veya hatalı testler başarı sayılmaz.
- RBAC/workspace, HttpOnly oturum, şifreli özel kayıtlar, redakte edilen kanıt ve Markdown/HTML/JSON indirme.

Düzeltmeler bu platformun yerel uygulama kontrol katmanına ait yapılandırmalardır. Genel depo kaynak kodunu otomatik değiştirme veya üretime deployment yapılmaz. Semantik Judge ayrı bir çağrı/rol ve değerlendirme protokolüdür; aynı modelin iki deployment'ta kullanılması istatistiksel bağımsızlık kanıtı değildir. Gerçek model dayanıklılığı, maliyet ve adaptif yöntem üstünlüğü için ayrıca gerçek hedef ölçümü gerekir.

## Docker/PostgreSQL seçeneği

`.env` içine güçlü `AEGIS_POSTGRES_PASSWORD` ekleyin; `docker compose up --build` çalıştırın. Web 3002, API 8002 portundadır. Yerel model host işletim sistemindeyse endpoint için `http://host.docker.internal:11434/v1` kullanın. Veritabanı ve vault anahtarı ayrı kalıcı volume'larda tutulur; yedekleri birlikte saklayın. Docker yapılandırması bu Windows oturumunda container çalıştırılarak doğrulanmadı.

## Eşit kaynak sınırlarında karşılaştırma

`scripts/benchmark.py --target-id TARGET_ID --runs 3` kayıtlı hedefin dondurulmuş kopyasında sabit test listesi, gözlemsiz model üretimi ve adaptif keşfi karşılaştırır. Ayrı benchmark veritabanı API worker'larıyla yarışmaz. Hedef revision, kapsam, kaynak sınırları ve gerçek tüketim JSON'da korunur. `--fixture --runs 1` yalnız orkestrasyonu test eder; gerçek model üstünlüğünü ölçmez. Sonuç varsayılan olarak `.runtime/benchmark.json` dosyasına yazılır. Windows'ta komutun başına `.\.venv-win\Scripts\python.exe` ekleyin.
