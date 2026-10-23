# Personal AI Live Voice Translator

ذاتی Windows 11 مترجم کا مرحلہ وار پروجیکٹ۔ صرف اردو ↔ انگریزی؛ development setup اور مقامی مائیک/playback کا ٹیسٹ مکمل ہیں۔ یہ ابھی قابلِ استعمال translator نہیں ہے۔ مکمل مراحل اور قبولیت کے معیار [PLAN.md](PLAN.md) میں ہیں۔

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
