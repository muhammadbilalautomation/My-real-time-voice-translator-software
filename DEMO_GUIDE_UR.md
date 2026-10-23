# اردو ↔ انگریزی: پہلے ترجمہ ڈیمو کی ہدایات

یہ short-utterance ڈیمو ہے، مسلسل live meeting translator ابھی نہیں۔ Zoom/Meet کو تبدیل نہ کریں؛ virtual audio driver ابھی نصب نہیں۔

رفتار کی تازہ تبدیلی: API upload کے لیے low-pass کے بعد 16kHz mono آڈیو استعمال ہوتی ہے، اصل recording برقرار رہتی ہے۔ ماڈل کا minimal thinking صراحت سے منتخب ہے۔ processing کے دوران timer اور 10s بعد slow-response اطلاع آتی ہے۔ ایک 6.2s synthetic Urdu sample کا ترجمہ 2.29s میں ملا؛ صارف کے پہلے 29.5s والے نتیجے کا سبب قطعی طور پر معلوم نہیں، اور یہ یکساں آڈیو کا A/B benchmark نہیں۔ آواز بننے کا وقت الگ ہے۔

## کھولنا اور آزمانا

1. AirPads pro کو پہلے Windows سے connect کریں۔ `Start-Translator-Demo.cmd` کو File Explorer میں double-click کریں۔ Codex میں فائل کھولنے سے صرف code نظر آتا ہے۔
2. Microphone میں Realtek، Playback میں AirPads pro منتخب رکھیں۔ دوسری recording ایپ بند رکھیں۔
3. Direction میں `Urdu → English` منتخب کریں۔ Record دباکر 3–10 سیکنڈ کا مکمل جملہ کہیں، مثلاً: «آپ کے پروجیکٹ پر 7 دن لگیں گے اور قیمت 500 ڈالر ہوگی۔»
4. Stop دبائیں، پھر Translate recording۔ زیادہ سے زیادہ 20 سیکنڈ record ہو سکتے ہیں؛ 20 سیکنڈ پر خود رکتا ہے۔
5. اصل پہچانا ہوا متن اور ترجمہ دیکھیں۔ Listen translation دباکر انگریزی سنیں۔ Original بٹن صرف آپ کی اصل recording سناتا ہے۔
6. الٹی سمت کے لیے `English → Urdu` منتخب کریں، پھر خود یہ test sentence بولیں: “The price is 500 dollars, not 5000.” اور وہی steps دہرائیں۔
7. مائیک کے بغیر متن آزمانے کے لیے Original خانے میں لکھ کر Translate typed text دبائیں۔

## کنٹرول اور privacy

- Record خود سے شروع نہیں ہوتا۔ Translate پر audio/text Google کو جاتا ہے۔ مفت درجے میں Google کی data-use terms لاگو ہیں؛ فرضی گفتگو سے ٹیسٹ کریں۔
- کوئی recording یا transcript مقامی disk پر خودکار محفوظ نہیں ہوتی۔ microphone playback کے ساتھ بیک وقت record نہیں ہوتا۔
- Stop processing کے نتیجے کو نظرانداز کرتا ہے؛ پہلے سے بھیجی HTTPS request کو سرور سے واپس نہیں لے سکتا۔ دیر سے آیا جواب خود نہیں چلے گا۔
- مشکوک نتیجے پر Listen بند رہے گا؛ دوبارہ Record کریں۔ اگر input dropout ہوا ہو تو recording بھیجنے کے بجائے دوبارہ بولنے کا پیغام آئے گا۔
- AI کبھی غلط سمجھ کر بھی confidence دکھا سکتا ہے؛ ہر غلطی کی شناخت کی ضمانت نہیں۔ قیمت، نفی، مدت اور نام خود بھی دیکھیں۔
- آواز کی ہلکی صفائی اور volume آزمودہ local playback path استعمال کرتے ہیں۔ گم شدہ یا clipped بات واپس نہیں بناتے۔
- ایپ billing خودکار فعال نہیں کرتی، model switching یا paid fallback نہیں کرتی؛ quota error پر رکتی ہے۔ کسی پہلے سے billed Google project کی billing state app خود verify نہیں کرتی۔

## اپنی آواز تیار کرنا — انسانی recording ابھی درکار ہے

پہلا demo default میں Preset AI voice استعمال کرتا ہے۔ یہ آپ کی آواز کی نقل نہیں۔

`Set up my voice` کھولیں:

1. خاموش ماحول میں Record دباکر اپنی عام اردو آواز میں 10–30 سیکنڈ بولیں۔ Stop، Original سے سنیں، پھر Use recording as reference دبائیں۔
2. دوبارہ Record دباکر نیچے دیا جملہ خود مکمل بولیں۔ Stop، اپنی آواز سنیں، پھر Use recording as consent دبائیں:

> I am the owner of this voice and I consent to Google using this voice to create a synthetic voice model.

اس کا مطلب ہے: یہ میری آواز ہے اور میں Google کو اس سے مصنوعی آواز بنانے کی اجازت دیتا ہوں۔

3. صرف اپنی حقیقی آواز اور اپنی رضامندی استعمال کریں۔ بالغ مالک ہونے اور Google کو نمونے بھیجنے کا checkbox منتخب کریں، پھر Create my voice دبائیں۔ Google قبول نہ کرے تو error پر رکیں؛ کوئی paid upgrade یا persistent cloud profile fallback نہیں ہوتا۔
4. کامیابی کے بعد setup بند کریں، Urdu → English کے لیے My voice منتخب کریں۔ پہلے سے بنائی گئی translation audio کی cache اس انتخاب پر صاف ہو جاتی ہے؛ دوبارہ Listen دبائیں۔ English → Urdu میں preset voice رہے گی۔

Google دونوں نمونے چیک کرتا ہے۔ یہ ایپ consent audio خود نہیں بناتی۔ `store=False` کے ساتھ عارضی encrypted key `.voice-profile.json` میں مقامی طور پر رہتی ہے، تقریباً 7 دن کے لیے؛ وہ Git سے خارج ہے۔ اصل reference/consent audio files محفوظ نہیں ہوتیں۔ key ختم ہو تو setup دوبارہ کرنا ہوگا۔ بالکل یکساں آواز یا غیر robotic نتیجے کی ضمانت نہیں؛ آپ سن کر معیار بتائیں گے۔

## آزمودہ نتائج اور حدود

مصنوعی اردو اور انگریزی speech سے دونوں سمتیں آزمائی گئیں؛ translation تقریباً 2.8–3.5s، مختصر TTS تقریباً 2.8–4s ان مخصوص tests میں۔ recording کا وقت اور playback کی مدت ان اعداد میں شامل نہیں۔ یہ مسلسل live latency کی پیمائش نہیں اور آئندہ رفتار کی ضمانت نہیں۔

12 offline checks (بشمول key redaction اور stateless voice profile): silence، clipping، wrong-language output، changed numbers، incomplete responses، cleanup preservation، canceled late responses، unclear speech lock، review-before-speak، laptop layout۔ حقیقی microphone-to-translation demo کی صارف کی تصدیق ابھی باقی ہے۔

## Official references (2026-10-23)

- [Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Audio understanding](https://ai.google.dev/gemini-api/docs/audio)
- [Speech generation](https://ai.google.dev/gemini-api/docs/speech-generation)
- [Voice replication and consent](https://ai.google.dev/gemini-api/docs/voice-replication)
- [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
