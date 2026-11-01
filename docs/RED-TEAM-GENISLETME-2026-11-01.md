# Red kaynak ve ara? geni?letmesi ? 2026-11-01

?lk 1.722 kaynakl?k k?t?phane s?n?rl? bir ba?lang??t?. G?ncel yerel snapshot 254.368 benzersiz kay?t, 16.832 taktik, 59 kaynak temelli mekanizma grubu ve 49 ger?ek yerel d?n???m i?eriyor. 90 birincil kaynak ba?lant?s? denetlendi; envanter her kayna??n mevcut ba?lant? durumunu ayr? g?sterir.

## Uzun ara?t?rma listesi

[90 kaynakl?k ayr?nt?l? envanter](RED-TEAM-KAYNAK-ENVANTERI.md), [makine taraf?ndan okunabilir envanter](red-team-source-inventory.json), [indirilen dosyalar?n URL/SHA-256 snapshot kayd?](red-team-corpus-snapshot.json). Framework, veri, algoritma, de?erlendirme, savunma ve referans kategorileri birbirinden ayr?d?r. HEAD ba?lant? denetimi paketin b?t?n yeteneklerinin denendi?i anlam?na gelmez.

## Ba?lanan veri ve bile?enler

| Kaynak | Benzersiz kay?t | Ger?ek ba?lant? |
|---|---:|---|
| TensorTrust v2 | 235.360 | ?nsan sald?rgan girdileri; oyun parola, savunma, cevap ve kimlik alanlar? ithal edilmez |
| WildTeaming | 16.833 | 16.832 taktik tan?m? + upstream composition prompt; Red sonraki ?a?r?da aday ?retir |
| BIPIA | 250 | Yazarlara ait text/code attack ?ablonlar?; d?? ta??y?c? veri k?meleri ithal edilmez |
| InjecAgent | 62 | Sald?rgan talimatlar?; mevcut target ara?lar?na uyarlan?r |
| HarmBench | 137 | GPTFuzzer seed ve literal ?ablon par?alar?; benchmark motoru ?al??t?r?lmaz |
| AgentDojo | 4 | Literal tool-result sald?r? ?ablon par?alar?; tam ajan ortam? ?al??t?r?lmaz |
| PyRIT 1.1.0 | 920 | Ger?ek kaynaklar ve 32 convert_async yap?land?rmas? |
| Garak 0.17.1 | 802 | Ger?ek kaynaklar ve 2 yerel buff |
| Promptfoo 0.125.1 | ? | Public redteam.Strategies.action API ?zerinden 11 yerel strateji |
| DeepTeam 1.0.10 | ? | Base64, ROT13, Leetspeak, CharacterStream s?n?flar?n?n ger?ek enhance API ?a?r?lar? |

Toplam: 237.420 seed + 16.832 taktik + 116 y?nerge par?as? = 254.368 kay?t. Kaynak sat?rlar? ve mekanizma gruplar? semantik olarak ?rt??ebilir. WildTeaming makalesindeki semantik k?meler, raw taktik kay?tlar?yla ayn? say? de?ildir; burada her kay?t ba??ms?z algoritma olarak sunulmaz. Ayn? kodlaman?n farkl? framework uygulamalar? d?n???m say?s?nda ayr? yer al?r.

TensorTrust ham 563.349 kay?ttan 147.705 self-attack, 7.199 bo?/do?ru-parola girdisi ve 24.149 tek kod tahmini ??kar?ld?. Kalan 384.296 kullan?labilir kay?ttan 235.360 yeni benzersiz metin al?nd?. WildTeaming dosyas?nda 16.833 ham taktik ba?l??? var; bo? tan?m ??kar?ld???nda 16.832 taktik kal?yor. Tekrarlanan definition listeleri ay?kland?; orijinal excerpt/reason/kimlik listeleri Red taktik kay?tlar?na aktar?lmad?. Upstream composition prompt referans metni olarak korunur.

## Native ara? ak???

inspect_target ? get_attack_method / get_attack_bundle ? search_attack_resources / get_attack_resource ? compose_attack_tactics ? gerekirse transform_attack ? submit_attack. list_attack_sources ve list_attack_methods ke?if sa?lar.

Korpus SQLite FTS5 ?zerinde sorgulan?r; kaynak metinlerinin y?z binlercesi prompt veya belle?e topluca y?klenmez. Tam kay?t iste?inde metin kesilmez. G?zlenen tactic aramalar? translation 20,21 ms, roleplay 6,23 ms, metadata 0,94 ms; library y?kleme yakla??k 0,235 saniye. Bu ?? ?rnek bir performans SLA de?ildir.

?neri ?nceki y?ntem ve kaynak kullan?m?ndan daha az kullan?lan uyumlu se?enekleri se?er. Varsay?lan ?ablon offset i?lem kimli?inden t?retilir; modelin s?rekli ilk iki kayda d?nmesi azalt?l?r. Bundle taktikleri biti?ik bir blok yerine ba??ms?z konumlardan se?er. A??k offset, arama ve alternatif taktik se?imi korunur. 59 grup, ger?ek corpus sorgular?na veya ?nceden indeksli upstream ?ablonlara dayan?r.

Ara? ??kt?lar? private kayda al?n?r; replay s?ras?nda provider/framework ?a?r?s? yinelenmez. Kaynak kimlikleri, s?r?m/lisans/hash, se?ilen taktikler, ger?ek composition prompt hash ve d?n???mlerin applied flag bilgisi sunucunun red_strategy kayd?na ba?lan?r. compose_attack_tactics upstream prompt ve se?ilen tan?mlar? birle?tirir; ba??ms?z WildTeaming pruning/scoring motoru ?al??t?rd??? iddia edilmez. JSON fallback kaynak/bundle ?n y?klemesini kullan?r ve native ara? ?a?r?s? iddia etmez.

D?n???m ??kt?s?n?n insertion_token de?eri payload alanlar?nda tam metinle de?i?tirilir. Token ba?ka bir d?n???m?n girdisinde de kullan?labilir. Aday?n karakter limitleri yerle?tirme sonras? do?rulan?r. Red ad?m ve output ?st s?n?rlar? mevcut 0/None ayarlar?yla korunur; kaynak sayfalama boyutlar? modelin toplam ?retim veya d???nme s?n?r? de?ildir.

## Do?rulama

66/66 backend testi ge?ti. Son kaynak ?rnekleme de?i?ikli?inden sonra ilgili 29 test tekrar ge?ti. ?ndeks arama, read-only eri?im, pagination, global dedup/provenance alias, Unicode scalar d?n???m?, veri alanlar?n?n d??lanmas?, native bundle/composition dispatch, replay, API authentication, tam metin okuma ve d?rt DeepTeam API bile?eni kontrol edildi. Frontend production build ve TypeScript ge?ti. Playwright: arama, source filtresi, farkl? sonraki sayfa, tam kay?t okuma, 90 kaynak tablosu ve inventory filtresi ge?ti; browser runtime hatas? 0.

Canl? FW-GLM-5.3 ?retim deneyi:

| Aile | Dil | Tur | S?re (sn) | Native / ge?erli |
|---|---|---:|---:|---|
| direct_injection | tr | 1 | 87.451 | Evet |
| indirect_injection | tr | 1 | 89.918 | Evet |
| tool_misuse | az | 1 | 84.724 | Evet |
| encoding_evasion | en | 1 | 99.173 | Evet |
| schema_abuse | en | 1 | 95.291 | Evet |
| multi_turn_manipulation | az | 3 | 101.076 | Evet |

6/6 native teslim, 43 provider ?a?r?s?, 50 farkl? taktik kayd? okuma, 20 farkl? taktik bile?imi girdisi ve 6 composition ?a?r?s?. Kullan?lan kaynaklar: bipia, injecagent, pyrit, tensortrust, wildteaming. Ger?ek deepteam:Leetspeak ??kt?s? payload'da applied=true olarak do?ruland?. Truncation g?zlenmedi.

JSON aday?, alan enum/const kurallar?n? ger?ek belge verisine ?st?n g?steren sahte bir response contract kulland?. ?ok turlu aday ilk turda normal belge sorusu, ikinci turda sahte konu?ma kayd?, ???nc? turda yeni talimatla ilerledi. Baz? adaylar h?l? administrator/audit framing kullan?yor: bu test say?s? b?t?n havuzun semantik ?e?itlili?ini veya tekrar oran?n? kan?tlamaz. Kaynak okuma ve composition kayd? da her takti?in payload ?zerinde etkin oldu?unu otomatik olarak kan?tlamaz.

Bu deneylerde target_calls=0, judge_calls=0 ve target_asr=null. 6/6 ge?erli aday, hedefte %100 sald?r? ba?ar?s? de?ildir. Yerel hedef model se?imi/indirmesi/deploy g?revi bekletiliyor.

Canl? kan?t dosyalar?: .runtime/live-red-expanded-composition.json, live-red-expanded-deepteam.json, live-red-expanded-json.json, live-red-expanded-dialogue.json; birle?ik metrikler .runtime/red-expanded-validation.json. Test XML: .runtime/red-expanded-pytest.xml ve red-sampling-pytest.xml. UI kan?t?: .runtime/red-library-expanded-ui.json ve red-library-expanded-ui.png.

## A??k aray?z ve kurulum

G?ncel aray?z ?nizlemesi: http://127.0.0.1:3004; API 127.0.0.1:8004. Ayr? preview veritaban? kullan?l?r; preview kampanya worker'lar? ba?lat?lmam??t?r. Ger?ek Red ara? zinciri yukar?daki canl? ?retim scriptleriyle ?al??t?r?ld?. ?nceki 3002/8002 s?re?leri yeniden ba?lat?lmad?. Son ?rnekleme de?i?ikli?i dosyalarda ve canl? scriptlerde aktiftir; kal?c? uygulama s?re?leri sonraki normal yeniden ba?latmada g?ncel kodu y?kler.

```powershell
.\.venv-win\Scripts\python.exe scripts\setup_redteam_tools.py --with-deepteam
.\.venv-win\Scripts\python.exe scripts\expand_redteam_library.py
.\.venv-win\Scripts\python.exe scripts\test_red_live.py --families schema_abuse --method wild_json_carrier --tool-mode native
```

setup_redteam_tools.py --index-only mevcut corpus i?aret?isini korur. expand_redteam_library.py --offline indirilmi? dosyalardan korpusu tekrar ?retir. Dosyalar main dal?ndan al?n?r ve ger?ek SHA-256 kay?tlar? tutulur; yeni bir ?evrimi?i snapshot say?lar? de?i?tirebilir. Ge?ici veritaban? tamamland?ktan sonra canl? corpus atomik olarak de?i?tirilir.

WildJailbreak eri?im ?artlar? kabul edilmedi; veri k?mesi ba?lanmad?. TensorTrust/WildTeaming veri deposunda a??k lisans saptanmad? (oyun kodu lisans? veri lisans? olarak kullan?lmad?); yerel ara?t?rma snapshot'lar? Git'e aktar?lmaz. BIPIA ta??y?c? veri istisnalar? nedeniyle yaln?z MIT attack ?ablonlar? al?nm??t?r. AgentHarm ve model/dataset kaynaklar?n?n ayr? ?artlar? envanterde belirtilir. .env, .runtime ve sanal ortamlar ignored durumdad?r.
