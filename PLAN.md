# Personal AI Live Voice Translator — مرحلہ وار منصوبہ

## کام کرنے کا اصول
ایک وقت میں صرف ایک مرحلہ۔ اس کے قبولیت کے معیار مکمل اور صارف کو نتیجہ دکھانے کے بعد اگلا مرحلہ شروع ہوگا۔ ناکامی کو کامیابی ظاہر نہیں کیا جائے گا۔

## موجودہ حالت
مرحلہ 4 کے لیے صارف کی اپنی آواز سے دونوں سمتوں کا متن/پلے بیک اور تازہ مردانہ preset قابلِ قبول ہونے کی تصدیق مل گئی۔ مرحلہ 5 صارف کی ہدایت پر مؤخر ہے۔

مرحلہ 6 جاری: live_audio.py اور live_demo.py میں حقیقی مسلسل WebSocket translation، 100ms mic blocks، Puck، text streams، mic/audio mute، Stop، bounded queues اور feedback روکنے کے لیے headphone-only audible output شامل ہیں۔ 24 offline tests کامیاب۔ دونوں سمتوں کے synthetic continuous tests میں input ختم ہونے سے پہلے audio ملا (3.91s/11.44s Urdu، 4.15s/7.48s English)۔ English→Urdu کے ایک جملے میں tense drift دیکھی گئی؛ step 6 مکمل یا meeting-ready نہیں۔ manual reviewed translation کے تمام safeguards live model پر خودبخود لاگو نہیں ہوتے۔ حقیقی headset/mic streaming کی صارف کی جانچ باقی ہے۔

فائنل UI کی صارف کی ضرورت: install ہونے والی local Windows app، web interface اور مقامی Python audio backend؛ ابھی یہ UI/installer نہیں بنا۔ اس کام کو stage 7 میں عمل میں لائیں گے؛ live stage کی تصدیق پہلے۔
تازہ صارف فیصلہ: فی الحال voice cloning مؤخر؛ کوئی مزید نمونہ یا consent recording درکار نہیں۔ قدرتی، نسبتاً نوجوان مردانہ AI preset منتخب کرنا ہے۔ Google catalog میں Puck male/upbeat/conversational ہے؛ اسے default کیا، اسکرین سے My voice/setup ہٹا دیے۔ حقیقی 19 سالہ آواز یا مکمل قدرتی نتیجے کی ضمانت نہیں؛ صارف سماعت سے معیار بتائے گا۔ cloning backend محفوظ ہے مگر عام test UI سے دستیاب نہیں۔ مرحلہ 5 کو اس وقت requirement کے طور پر روک کر preset voice کے ساتھ اگلا کام کیا جا سکتا ہے۔
فعال سیشن: 2026-10-23، پاکستانی وقت 10:32 پر ترجمہ ڈیمو کا کام شروع؛ صارف کا ہدف 12:30–13:00۔ API key کی موجودگی اور authentication چیک؛ key output/log/GitHub میں ظاہر نہیں کی گئی۔

Voice setup کی اصل HTTP400 وجہ schema-only درخواست سے ثابت ہوئی: Google نے gemini-3.8-flash-lite-tts کو voice creation model کے طور پر رد کیا اور voice.model ہٹانے کو کہا۔ creation سے model ہٹا دیا؛ اب schema-only جواب Missing source_audio ہے، یعنی پہلے والا model rejection ختم ہے۔ حقیقی نمونوں سے voice creation ابھی تصدیق طلب ہے۔ audio24kHz میں بھیجی جاتی ہے، sequential reference/consent recording خود منتخب ہوتی ہے؛ بڑے اردو تلفظ سے English consent پڑھنے میں مدد ملتی ہے۔ اصل server error یا key ظاہر نہیں کی جاتی۔

رفتار کا مسئلہ: صارف کے screenshot میں translation 29.5s۔ upload کے لیے anti-aliased 16kHz mono تبدیلی، explicit minimal thinking اور live waiting timer شامل؛ 16 offline tests کامیاب۔ مختلف 6.2s synthetic audio پر translation 2.29s؛ پچھلے وقت کا exact cause ثابت نہیں، صارف کا دوبارہ ٹیسٹ باقی ہے۔

مرحلہ 3 مکمل: موجودہ official pricing/audio/TTS docs دیکھے، accessible models چیک ہوئے۔ gemini-2.5-flash-lite نے نئے صارف کے لیے 404 دیا؛ gemini-3.5-flash-lite کامیاب۔ gemini-3.8-flash-lite-tts سے English اور Urdu synthetic speech کامیاب۔ صرف public free-tier eligible models استعمال ہوئے؛ کوئی billing account، purchase یا paid fallback فعال نہیں کیا۔ باقی account quota یا billing state صرف authentication سے معلوم نہیں ہوتی؛ پورے مہینے مفت meetings کی ضمانت نہیں۔

مرحلہ 4: text اور synthetic audio سے دونوں سمتیں کامیاب؛ 500/5000، 7 دن، نفی، embedded instructions اور نامکمل جملے آزمائے۔ local silence/clipping gates، غلط output script، اعداد کی تبدیلی، نامکمل response پر تحفظ؛ 12 offline tests کامیاب۔ short-utterance demo تیار، صارف کی اصل آواز کے ساتھ استعمال کی تصدیق زیرِ انتظار۔

مرحلہ 5 کی تیاری: official Google voice replication endpoint دستیاب؛ 10–30s حقیقی reference اور اسی بالغ شخص کی exact consent recording درکار۔ voice_setup.py میں دستی recording/preview/selection اور explicit consent checkbox تیار؛ cloud upload صرف Create پر۔ stateless voice key مقامی ignored file میں، تقریباً 7 دن؛ کوئی actual user voice profile ابھی نہیں بنایا۔ انسانی recordings اور voice similarity کی تصدیق کے بغیر مرحلہ 5 مکمل نہیں ہوگا۔ مراحل 6–10 شروع نہیں ہوئے۔

مرحلہ 1 مکمل (2026-10-23): Python 3.13.15 x64، pip، مقامی .venv، Tcl/Tk 8.6.15، sounddevice 0.5.6 اور numpy 2.5.4 کی تصدیق ہوئی۔ pip check کامیاب، imports کامیاب، اصل Tk window initialization کامیاب، audio enumeration کامیاب: Realtek microphone اور speakers دستیاب۔ صرف devices دریافت کیے؛ recording/playback شروع نہیں کیے۔ requirements-lock.txt میں آزمودہ dependencies درج ہیں۔ .env، .venv، recordings اور logs کا Git سے خارج ہونا چیک کیا۔ یہ مرحلہ 1 کی ابتدائی جانچ کا نتیجہ ہے۔
GitHub origin: https://github.com/muhammadbilalautomation/My-real-time-voice-translator-software.git — development setup کی فائلیں اسی repository میں محفوظ کی جائیں گی۔

مرحلہ 2 مکمل (صارف کی سماعت سے تصدیق): audio_test.py اور Start-Audio-Test.cmd تیار ہیں۔ GUI initialization، input/output format support اور idle حالت میں recording بند ہونے کی جانچ کامیاب۔ Realtek microphone اور AirPads pro playback منتخب ہیں۔ صارف نے recording/playback آزمایا اور ہلکی صفائی کے بعد آواز درست ہونے کی تصدیق کی۔ مقامی audio-test میں آڈیو صرف RAM میں ہے؛ فائل یا network پر نہیں جاتی۔ translator demo میں Translate دبانے پر Google کو جاتی ہے۔

صارف نے playback میں ہلکی distortion بتائی۔ stability buffering، اختیاری ہلکی DC/headroom/fade processing، playback volume اور clipping/dropout warnings بہتر کیے؛ synthetic signal checks کامیاب۔ صارف نے دوبارہ سن کر آواز کو قابلِ قبول قرار دیا؛ distortion کے اصل سبب کی قطعی تشخیص نہیں ہوئی۔

## 10 مراحل اور قبولیت کے معیار
1. **Development setup:** Python 3.13 x64، pip، tkinter کی تصدیق؛ مقامی .venv؛ صرف sounddevice اور numpy؛ pip check اور imports کامیاب؛ بغیر recording کے audio devices کی فہرست؛ Git میں secrets خارج۔
2. **Local audio:** مائیک/ہیڈفون انتخاب، level indicator، مختصر ریکارڈنگ اور playback، Stop؛ صارف صاف آواز کی تصدیق کرے۔ ریکارڈنگ صارف کے بٹن سے شروع ہو۔
3. **Gemini feasibility:** موجودہ official model/API، Urdu support، free quota، privacy اور session constraints کی دوبارہ تصدیق؛ مقامی .env؛ فرضی مختصر آڈیو اور متن سے مفت رسائی چیک۔ paid fallback نہیں۔
4. **Faithful two-way text translation:** Urdu/English input recognition اور translation؛ اعداد، قیمت، تاریخ، نفی، نام اور غیر واضح آڈیو کے ٹیسٹ۔ کوئی embellishment نہیں؛ غیر واضح جملہ روک کر مقامی اطلاع۔ ہر recognition error معلوم ہونے کی ضمانت نہیں۔
5. **Personal voice feasibility:** صرف صارف کی اجازت یافتہ آواز کے نمونے؛ مفت/local طریقے کے license، hardware، latency اور معیار کی جانچ۔ قدرتی مشابہ English speech۔ اگر قابلِ قبول مفت راستہ نہ ملے تو رکاوٹ واضح اور صارف کا فیصلہ؛ یہ requirement خاموشی سے ختم نہیں ہوگی۔
6. **Translation audio engine:** سمجھ آنے والی مکمل بات سے translated audio؛ output language checks، queues، duplicate prevention، mute، فوری stop، reconnect پر پرانے audio کی خودکار replay نہیں؛ latency measurement۔
7. **Desktop controls:** سادہ مقامی window، دونوں متن، الگ mute، devices، status/errors، محفوظ preferences؛ اہم بات کے لیے اختیاری review-before-send۔ Urdu captions صرف مقامی؛ meeting chat/captions میں کوئی write integration نہیں۔
8. **Virtual audio routing:** driver یا system setting سے پہلے تبدیلی کی وضاحت؛ پہلے سے اجازت شدہ scope دیکھنا؛ ضرورت پر صارف کی اجازت؛ meeting input/output الگ، generated audio capture سے خارج، normal devices پر واپسی کی ہدایات۔
9. **Zoom and Google Meet trials:** فرضی one-to-one calls، دونوں directions، اصل Urdu کی عدم ترسیل، feedback، mute، internet interruption؛ صارف کے سننے اور remote participant کے feedback سے تصدیق۔ remote client نے حقیقتاً کیا سنا یہ مقامی app یقینی نہیں جان سکتی۔
10. **Readiness and delivery:** طویل فرضی meeting، noise/cut audio/number tests، secrets/logging check، version lock، beginner Urdu setup اور recovery guide؛ GitHub link اور access ملنے پر محفوظ code push؛ unresolved limitations کی واضح رپورٹ۔

## دائرۂ کار
Windows 11؛ صرف Urdu ↔ English؛ الگ translator app، Zoom/Meet کی replacement نہیں؛ Gemini کے لیے internet؛ client پر app نصب نہیں۔ mobile calls، cloud accounts/database، voice cloning کے paid subscriptions، recording/history default طور پر شامل نہیں۔ اصل raw audio کو لفظی طور پر English نہیں بنایا جا سکتا؛ مشابہ synthesized voice ہدف ہے۔

## سیکیورٹی اور خرچہ
.env، keys، local recordings، logs اور .venv Git سے خارج۔ key چیٹ میں نہ دیں۔ کوئی paid service خودکار فعال نہیں ہوگی۔ audio/text مستقل محفوظ کرنا default off؛ cloud translation میں آواز provider کو جاتی ہے۔ free tier کی privacy پہلے سمجھانا ضروری ہے۔

## وقت
وقت کا حتمی وعدہ نہیں۔ مراحل 3، 5 اور 8 کے تجربات کے بعد قابلِ اعتماد تخمینہ؛ code generation کی رفتار کو مکمل meeting reliability نہ سمجھا جائے۔
