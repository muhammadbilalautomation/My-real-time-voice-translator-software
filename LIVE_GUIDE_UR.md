# مسلسل ترجمے کا تجربہ

`Start-Live-Demo.cmd` کو File Explorer میں double-click کریں۔ یہ الگ تجرباتی ونڈو ہے؛ Zoom/Meet کی settings ابھی نہ بدلیں۔

1. اردو بولنے کے لیے `Urdu → English` منتخب رکھیں۔
2. صرف ایک مرتبہ **Start Live / مسلسل شروع** دبائیں۔ کنکشن تیار ہونے کا پیغام آنے دیں۔
3. عام انداز میں چند مکمل جملے بولیں۔ اصل اور ترجمہ شدہ متن آپ کے بولتے ہوئے آنے لگے گا۔ ہر بار Record، Translate یا Listen دبانے کی ضرورت نہیں۔
4. **Stop** سے سیشن بند کریں۔ زبان یا devices بدلنے سے پہلے Stop کریں۔

## آواز کیسے سننی ہے؟

ایئربڈز پہلے connect کریں، پھر ونڈو کھولیں تاکہ نئی device فہرست میں آئے۔ Playback میں Headphones/Headset منتخب کریں اور **ترجمے کی آواز سنیں** منتخب کریں۔ Start کے بعد مسلسل Puck مردانہ آواز ملے گی۔

اگر صرف Speakers منتخب ہوں تو ایپ ترجمے کی آواز فعال نہیں کرے گی؛ متن چل سکتا ہے۔ یہ اپنی پیدا کردہ آواز دوبارہ سن کر feedback بنانے سے بچانے کا انتظام ہے۔ headphone کا نام ملنا اصل acoustic isolation کی ضمانت نہیں؛ واقعی ایئربڈز پہن کر استعمال کریں۔

**اپنا مائیک خاموش کریں** نئے microphone samples اور unsent queue کو خاموش کرتا ہے؛ پہلے سے Google کو پہنچے الفاظ واپس نہیں لیے جا سکتے۔ ترجمے کی آواز کا checkbox بند کرنے سے playback queue صاف اور آئندہ آواز بند ہوتی ہے۔ Stop تمام مقامی queued audio خارج کرتا ہے، connection خودکار replay/reconnect نہیں کرتا۔

## کیا آزمایا گیا؟

- اصل WebSocket setup کامیاب؛ translation-specific model اور Puck config قبول۔ مکمل model list کے لیے pagination لحاظ سے `pageSize=1000` استعمال کیا؛ پہلی default page میں live models نہ ہونے سے پہلے کی discovery نامکمل تھی۔
- 11.44s مصنوعی Urdu audio: پہلا English output audio 3.91s پر آیا، source بولنا ختم ہونے سے پہلے۔ مکمل متن میں نام، 7 دن اور $500 موجود تھے۔
- 7.48s مصنوعی English audio: پہلا Urdu output audio 4.15s پر آیا، بولنا ختم ہونے سے پہلے؛ ایک جملے میں present tense سے past tense کی غلط تبدیلی دیکھی گئی۔
- یہ synthetic tests حقیقی microphone، headset، noisy meeting یا مکمل دو طرفہ call کی جانچ نہیں۔ وقت کی ضمانت نہیں؛ recording، network اور model کے مطابق بدلتا ہے۔ UI میں first-audio وقت session کے آغاز سے ناپا جاتا ہے، speech onset سے نہیں؛ دیر سے بولنے کا وقت بھی شامل ہو سکتا ہے۔
- 24 offline checks میں resampling continuity، bounded playback، Stop پر صفائی، unsent mic mute، target echo off، speaker output block اور پرانے demo کے tests شامل ہیں۔

## حدود اور رازداری

یہ ابھی step 6 کا experiment ہے۔ ایک منتخب سمت فی سیشن آزمائیں؛ meeting audio routing اور بیک وقت دو الگ sessions ابھی شامل نہیں۔ Output میں language code مختلف ہو یا English target کے transcript میں Urdu script ہو تو مزید آڈیو روکتا ہے؛ transcript آنے سے پہلے خارج ہوا صوتی حصہ واپس نہیں لے سکتا۔

Live translation model مسلسل آڈیو براہِ راست بناتا ہے؛ manual demo کی JSON status/number checks اسی راستے میں لاگو نہیں ہیں۔ ہر عدد، نفی، نامکمل بات، phonetic transcription یا tense error معلوم کرنے کی ضمانت نہیں۔ اہم جملوں کے لیے manual reviewed demo موجود ہے۔ اس live experiment کو کلائنٹ کی میٹنگ میں ابھی استعمال نہ کریں؛ accuracy/latency tradeoff مزید جانچنا ہے۔

Start دبانے پر microphone کھلتا اور audio Google کو جاتا ہے۔ صرف memory buffers، کوئی recording file نہیں۔ key HTTPS/WebSocket header میں رہتی ہے، source یا output میں نہیں۔ paid fallback یا billing configuration فعال نہیں کی گئی۔ quota یا server error پر manual restart درکار ہے۔ input overflow یا lag پر source کے حصے خاموشی سے چھوڑنے کے بجائے سیشن error کے ساتھ رکتا ہے؛ playback 5s سے زیادہ پیچھے ہو تو سیشن روکتا ہے۔

فی الحال cloning مؤخر ہے؛ آواز ایک تیار شدہ male AI preset ہے۔

[Google Live Translation docs](https://ai.google.dev/gemini-api/docs/live-api/live-translate)
