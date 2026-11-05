# عينة الطفلة — v4

**عينة واحدة للمراجعة، وليست اعتمادًا احترافيًا نهائيًا أو ملف AEP محفوظًا.** After Effects غير موجود هنا؛ الفيديو اختبار حركة محلي، واختبارات PSD أُجريت في GIMP ثم قُرئت ببرنامج مستقل.

- [فيديو الاختبار المحلي — 12 ثانية](https://raw.githubusercontent.com/aya47192-blip/ae-codes/refs/heads/storyboard/lama-curly-layered-psd-v1/storyboards/lama-akbar/child-rig-pilot-v4/Leila-08-Local-Rig-Test-v4.mp4)
- [تحميل PSD الحقيقي داخل ZIP](https://raw.githubusercontent.com/aya47192-blip/ae-codes/refs/heads/storyboard/lama-curly-layered-psd-v1/storyboards/lama-akbar/child-rig-pilot-v4/Leila-08-Photoshop-Pilot-v4.zip)
- [مصدر بناء مشروع After Effects — JSX + PNG](https://raw.githubusercontent.com/aya47192-blip/ae-codes/refs/heads/storyboard/lama-curly-layered-psd-v1/storyboards/lama-akbar/child-rig-pilot-v4/Leila-08-AE-Builder-v4.zip)
- [مصادر طبقات الرسم](https://raw.githubusercontent.com/aya47192-blip/ae-codes/refs/heads/storyboard/lama-curly-layered-psd-v1/storyboards/lama-akbar/child-rig-pilot-v4/Leila-08-Layer-Sources-v4.zip)
- [صور تبديل الملابس](Leila-08-Wardrobe-Proof-v4.jpg)
- [صور إخفاء العين والنضارة](Leila-08-Face-Proof-v4.jpg)

كل طرف له أجزاء واحدة مرتبطة بالمفاصل. لا توجد صورة جسم كامل ثابتة تحت الأجزاء المتحركة. الشراب غير مرسوم على الجلد أو على الأحذية. البلوزة والفستان والشرابات والجزم مجموعات مستقلة، والأكمام وأجزاء الشراب تتبع عظام الجلد نفسها. الكفوف كاملة بدون فصل أصابع.

الاختبارات المحلية لم ترصد إيدًا أو كمًا أو ساقًا ثابتة باقية في أماكنها بعد تحريكها في وضعيات الفحص. هذه اختبارات محددة وليست ضمانًا لكل الحركات. نهايات المفاصل أُعيد رسمها لتسمح بالتداخل؛ تقييم التشريح وتشطيب التحريك والقماش داخل After Effects لا يزال مطلوبًا. الريج أمامي؛ القرفصاء والخطوات الجانبية اختباران وليسا إثباتًا لجلوس واقعي أو فيلم كامل.

لتكوين AEP: فكّي ضغط حزمة **AE Builder** بالكامل، افتحي مشروعًا فارغًا في After Effects وشغّلي `build_project.jsx` من File → Scripts → Run Script File، ثم احفظي باسم جديد. كومب `Leila_Rig` للتحكم اليدوي، و`Leila_Motion_Test` للاختبار. مفاتيح الملابس في `CTRL_Wardrobe`. يمكن بعد ذلك تشغيل `audit_native_project.jsx` لفحص حسابات القدم من داخل البرنامج. لا يوجد AEP مزيف أو فيديو مُدّعى أنه رندر AE.

[تفاصيل الاستخدام](README-AR.txt) · [التحقق والقيود](verification.json) · [حالة اعتماد الإنتاج](production-gate.json)

المناطق المخفية وأجزاء المفاصل مرسومة بمساعدة توليد الصور، والطبقات Raster. باقي الشخصيات لم تُعتمد بهذا البناء ولم يُعمّم عليها.
