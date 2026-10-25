# Personal AI Live Voice Translator

## لائیو خرابی کی اصلاح

Bluetooth reconnect کے بعد پرانی device IDs استعمال نہیں ہوتیں: Start/voice preview سے پہلے fresh list سے منتخب نام اور host API دوبارہ ملائے جاتے ہیں۔ غائب ایئربڈز پر API یا مائیک نہیں کھلتا۔ Device/network/access/quota کی الگ واضح errors، نئے error کو پرانے message سے نہ چھپانا، اور معلوم quota پر backend-enforced countdown شامل ہیں۔ [تصدیق اور باقی حدود](RELIABILITY_CHECKS.md)۔ 47 offline tests اور browser QA پاس؛ دونوں سمتوں کے مصنوعی Google Live + fixed male TTS tests کامیاب۔ اس سے انسانی سماعت یا لمبی meeting کی قابلِ اعتماد دستیابی ثابت نہیں ہوتی۔

## نیا مقامی انٹرفیس — v0.7

UI کی تازہ صفائی: compact Urdu workspace، forest sidebar، واضح transcript panels اور الگ **ترتیبات**۔ Settings میں نئی key password field میں پیسٹ کرکے محفوظ کریں؛ خانہ Save کے بعد صاف ہوتا ہے۔ محفوظ key کبھی واپس browser میں نہیں آتی اور نہ prefill ہوتی ہے۔ `POST /api/key` existing app token/Host/Origin checks کے تحت، صرف idle حالت میں `.env` atomically بدلتا ہے؛ نقطے والی key formats قبول ہیں۔ یہ schema validation ہے، Google authentication یا quota کی ضمانت نہیں۔ 41 offline tests پاس؛ browser میں save feedback/field cleanup کے لیے simulated API اور backend میں temporary `.env` استعمال ہوئی؛ اصل key ٹیسٹ سے نہیں بدلی گئی۔

اس لیپ ٹاپ پر `Start-Voice-Translator.cmd` یا Desktop کا **Bilal Voice Translator** شارٹ کٹ کھولیں۔ الگ Edge app window میں Urdu/English، devices، Start/Stop، mic mute، audio mute، voice preview، local captions اور اردو guide دستیاب ہیں۔ [آسان استعمال اور موجودہ حدود](APP_GUIDE_UR.md)۔ اضافی package، account، server hosting یا Windows setting کی تبدیلی درکار نہیں۔ یہ existing Python environment کے ساتھ مقامی app ہے؛ دوسرے کمپیوٹر کے لیے standalone EXE installer ابھی نہیں۔

Gemini Puck کی گفتگو والی metadata بہتر کی گئی اور streamed آڈیو کی resampling میں chunk continuity درست کی گئی۔ یہ انسانی سماعت میں معیار کی ضمانت نہیں۔ 2026-10-25 کی مختصر API probe نے 5.92s آڈیو 2.61s میں تیار کیا؛ یہ مکمل live round-trip latency نہیں۔

**یہ مقامی MVP ہے؛ مکمل Zoom/Meet ریلیز نہیں۔** منتخب input کا ترجمہ منتخب headphones میں آتا ہے۔ virtual audio routing، بیک وقت دو طرفہ meeting capture اور حقیقی remote-participant جانچ ابھی باقی ہے۔

سرور صرف `127.0.0.1:8765` پر سنتا ہے۔ محفوظ API key backend میں رہتی ہے؛ نئی key Settings میں صارف عارضی طور پر پیسٹ کرتا ہے اور save attempt کے بعد field صاف ہوتی ہے۔ مقامی control token، Host/Origin checks، restricted static routes، CSP، transcript bounds، explicit Start اور browser disconnect کے 30s بعد stop شامل ہیں۔ Stop دبائیں؛ صرف window بند ہونے پر منحصر نہ رہیں۔ `.env`، audio، browser test artifacts اور screenshots Git سے خارج ہیں۔ Browser میں دکھنے والا عارضی app token Gemini API key نہیں۔

تصدیق: 41 offline tests پاس؛ `& '.\.venv\Scripts\python.exe' -X utf8 -m unittest discover -v`۔ Browser QA: server کھول کر `playwright-cli -s=translator open http://127.0.0.1:8765`، پھر `playwright-cli -s=translator run-code --filename=qa/browser-check.js`۔ QA session routes کو simulate کرتا ہے؛ حقیقی mic/API نہیں کھلتے۔ موجودہ dependency versions وہی ہیں؛ کوئی نئی dependency شامل نہیں کی گئی۔ Bluetooth refresh idle حالت میں PortAudio lifecycle دوبارہ initialize کرتا ہے؛ sounddevice upgrade پر اس کا smoke test ضروری ہے۔ Windows port exclusive binding ایک وقت میں صرف ایک backend رکھتی ہے؛ دوسرا launcher اسی موجودہ app کو کھولتا ہے۔

ذاتی Windows 11 مترجم کا مرحلہ وار پروجیکٹ۔ صرف اردو ↔ انگریزی؛ development setup اور مقامی مائیک/playback کا ٹیسٹ مکمل ہیں۔ مکمل meeting translator ابھی تیار نہیں۔ مکمل مراحل اور قبولیت کے معیار [PLAN.md](PLAN.md) میں ہیں۔

اب مختصر جملوں کا دو طرفہ translation demo بھی دستیاب ہے: `Start-Translator-Demo.cmd`۔ [اردو ڈیمو ہدایات](DEMO_GUIDE_UR.md) پڑھیں۔ یہ مسلسل live translator یا Zoom integration نہیں۔ API key صرف local `.env` میں رکھیں؛ source میں نہیں۔ کوئی نئی Python dependency درکار نہیں؛ REST client standard library استعمال کرتا ہے۔

مسلسل ترجمے کا الگ تجربہ: `Start-Live-Demo.cmd`، [آسان Live ہدایات اور موجودہ حدود](LIVE_GUIDE_UR.md)۔ اس میں `websockets==17.3` استعمال ہوتا ہے؛ dependencies کی فائلیں اپ ڈیٹ ہیں۔ یہ ابھی accuracy اور headset testing کے مرحلے میں ہے، meeting integration نہیں۔

## مرحلہ 1 — مکمل

2026-10-23 کو اس لیپ ٹاپ پر جانچ:

- Python 3.13.15، 64-bit؛ project-local `.venv`؛ pip 26.2.1۔
- Tcl/Tk 8.6.15؛ Tk window initialize اور بند کرنے کی جانچ کامیاب۔
- sounddevice 0.5.6، numpy 2.5.4؛ متعلقہ dependencies `requirements-lock.txt` میں۔
- `pip check`: No broken requirements found۔
- آڈیو ڈیوائسز دریافت ہوئیں؛ default Realtek microphone اور speakers۔ فہرست میں نام آنے سے اصل recording/playback کی کامیابی ثابت نہیں ہوتی؛ یہ مرحلہ 2 میں آزمائیں گے۔
- کوئی آڈیو record، play یا Gemini کو ارسال نہیں کی گئی۔

## موجودہ environment کی جانچ

پروجیکٹ فولڈر میں PowerShell سے:

```powershell
& '.\.venv\Scripts\python.exe' check_setup.py
& '.\.venv\Scripts\python.exe' -m pip check
```

یہ commands صرف environment اور devices کی معلومات دکھاتی ہیں، recording شروع نہیں کرتیں۔ `.venv` activation یا PowerShell execution policy بدلنا ضروری نہیں۔ Python نصب ہونے سے پہلے کھلا terminal ہو تو عام `python` command استعمال کرنے سے پہلے نیا terminal کھولیں؛ اوپر دیا گیا project interpreter براہِ راست استعمال ہو سکتا ہے۔

## دوسرے کمپیوٹر پر setup

Python 3.13 x64 نصب ہونے کے بعد، project directory میں:

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements-lock.txt
& '.\.venv\Scripts\python.exe' check_setup.py
```

Dependencies صرف اسی project environment میں نصب کریں۔

## اس لیپ ٹاپ پر ڈاؤن لوڈ کا مسئلہ

`pypi.org` کا DNS جواب ناکام تھا جبکہ سرکاری `www.pypi.org` اور `files.pythonhosted.org` دستیاب تھے۔ صرف installation process میں DNS fallback استعمال کیا گیا؛ HTTPS hostname اور certificate verification برقرار رہی۔ Windows DNS، hosts file، firewall یا مستقل pip configuration تبدیل نہیں کی گئی۔ آئندہ pip download میں DNS error آئے تو network resolution دوبارہ چیک کرنا ہوگا؛ یہ مستقل network repair نہیں ہے۔

## محفوظ فائلیں

API key چیٹ یا source code میں نہ لکھیں۔ آئندہ `.env` میں مقامی طور پر رکھیں گے؛ `.env`، `.venv`، recordings، logs اور key files Git سے خارج ہیں۔ ابھی کسی API key کی ضرورت نہیں۔ کوئی paid service یا virtual audio driver نصب نہیں کیا گیا۔ GitHub remote جوڑا گیا ہے؛ اس repository میں صرف source، منصوبہ اور setup ہدایات محفوظ کریں۔

## مرحلہ 2 — مقامی آڈیو ٹیسٹ مکمل

`Start-Audio-Test.cmd` پر double-click کریں۔ ایئربڈز پہلے connect کریں؛ ڈیوائس بدلنے پر ونڈو بند کرکے دوبارہ کھولیں تاکہ فہرست تازہ ہو۔

1. Microphone میں Realtek اور Playback میں AirPads pro منتخب ہوں گے، اگر دستیاب ہوں۔ ضرورت پر فہرست سے تبدیل کریں۔
2. Record دبائیں اور معمول کی آواز میں 10 سیکنڈ بولیں۔ ریکارڈنگ خود رک جائے گی؛ Stop سے پہلے بھی روک سکتے ہیں۔ اس دوران آڈیو playback نہیں ہوتا۔
3. Play دبائیں؛ اپنی آواز ایئربڈز میں سنیں اور صفائی، اونچائی اور کٹنے کی کیفیت بتائیں۔ اس دوران microphone recording بند ہے۔
4. Stop سے playback فوراً روکیں۔ نئی recording پچھلی کو بدل دیتی ہے؛ ایپ بند کرنے پر recording ختم ہو جاتی ہے۔

ہلکی صفائی default on ہے: DC offset ہٹتا ہے، بہت اونچے playback peaks کم ہوتے ہیں اور صرف ابتدا/اختتام پر 5ms fade لگتا ہے۔ آواز کا pitch یا الفاظ نہیں بدلتے؛ denoising/voice enhancement شامل نہیں۔ اصل recording RAM میں الگ برقرار ہے؛ checkbox بند کرکے موازنہ کریں۔ Playback volume default 80% ہے، تبدیلی اگلے Play پر لگتی ہے۔ input/output کے لیے مستحکم high-latency buffering استعمال ہوتی ہے؛ یہ صرف مقامی ٹیسٹ ہے۔ پہلے سے clipped recording کی کھوئی تفصیل واپس نہیں آ سکتی؛ warning پر مائیک سے دور ہوکر دوبارہ بولیں۔

آڈیو صرف memory میں رہتی ہے؛ کوئی فائل، network request، translation یا voice cloning شامل نہیں۔ Windows microphone permission بند ہو تو واضح error آئے گا؛ permission خود سے تبدیل نہیں ہوتی۔ GUI اور supported audio formats چیک ہوئے ہیں؛ صارف نے actual recording/playback سن کر ہلکی صفائی کے بعد آواز قابلِ قبول ہونے کی تصدیق کی۔ یہ مترجم کا حتمی UI نہیں، صرف دوسرے مرحلے کی ٹیسٹ ونڈو ہے۔
