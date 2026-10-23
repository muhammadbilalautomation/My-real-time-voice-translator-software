# Personal AI Live Voice Translator — مرحلہ وار منصوبہ

## کام کرنے کا اصول
ایک وقت میں صرف ایک مرحلہ۔ اس کے قبولیت کے معیار مکمل اور صارف کو نتیجہ دکھانے کے بعد اگلا مرحلہ شروع ہوگا۔ ناکامی کو کامیابی ظاہر نہیں کیا جائے گا۔

## موجودہ حالت
مرحلہ 1 مکمل (2026-10-23): Python 3.13.15 x64، pip، مقامی .venv، Tcl/Tk 8.6.15، sounddevice 0.5.6 اور numpy 2.5.4 کی تصدیق ہوئی۔ pip check کامیاب، imports کامیاب، اصل Tk window initialization کامیاب، audio enumeration کامیاب: Realtek microphone اور speakers دستیاب۔ صرف devices دریافت کیے؛ recording/playback شروع نہیں کیے۔ requirements-lock.txt میں آزمودہ dependencies درج ہیں۔ .env، .venv، recordings اور logs کا Git سے خارج ہونا چیک کیا۔ مرحلہ 2 شروع نہیں کیا۔
GitHub origin: https://github.com/muhammadbilalautomation/My-real-time-voice-translator-software.git — development setup کی فائلیں اسی repository میں محفوظ کی جائیں گی۔

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
