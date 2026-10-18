# الواجهة المستدامة — تتبّع الصورة الأصلية

**[تحميل ملف الكاد فقط — ZIP](drawings/sustainable-facade/facade_cad.zip)** — افتحي الرابط واضغطي Download raw file (السهم لأسفل)، ثم فكّي الضغط وافتحي facade_cad.dxf داخل AutoCAD.

المصدر: [IMG_3106.PNG](IMG_3106.PNG). نسخة للمراجعة بخطوط سوداء موحّدة، PDF متجهي وDXF وAutoLISP. **ليست مطابقة مضمونة 100% ولا كل مساراتها مغلقة**؛ التفاصيل وحدود الفحص موضّحة في [تعليمات النسخة](drawings/sustainable-facade/README_AR.md).

[تحميل الحزمة كاملة](drawings/sustainable-facade/sustainable_facade_package.zip?raw=true) · [PDF](drawings/sustainable-facade/sustainable_facade.pdf?raw=true) · [DXF](drawings/sustainable-facade/sustainable_facade.dxf?raw=true) · [AutoLISP](drawings/sustainable-facade/sustainable_facade.lsp?raw=true)

![المعاينة](drawings/sustainable-facade/preview.png)

---

# الرسومات والمهارات

## الأحدث — محاولة من الريفرنس الأوضح

**[المعاينة](drawings/palace-reference-redraw/palace_reference_preview.png)** · **[تحميل الحزمة كاملة](drawings/palace-reference-redraw/palace_reference_package.zip?raw=true)**

- [PDF أساسي بدون أبعاد مضافة](drawings/palace-reference-redraw/palace_reference_redraw.pdf?raw=true)
- [AutoCAD DXF](drawings/palace-reference-redraw/palace_reference_redraw.dxf?raw=true)
- [كود AutoLISP مستقل](drawings/palace-reference-redraw/palace_reference_redraw.lsp?raw=true)
- [التشغيل والفحوص وحدود المطابقة](drawings/palace-reference-redraw/README_AR.md)

أُعيد ضبط الوردات والحجر وزخارف الإطارات والقواعد والعنوان. ما زالت بعض الزخارف تقريبية؛ ليست مطابقة حرفية مثبتة للريفرنس. المقاسات تقديرية. تشغيل LSP: **APPLOAD → PALACE**؛ الأبعاد الإضافية اختيارية.

![معاينة محاولة الريفرنس الأوضح](drawings/palace-reference-redraw/palace_reference_preview.png)


## الأحدث: AutoLISP كامل — واجهة منظّفة وأبعاد تقديرية

- **[تحميل الحزمة كاملة ZIP](drawings/palace-autolisp-clean/palace_autolisp_clean_package.zip?raw=true)**
- [تحميل AutoLISP LSP](drawings/palace-autolisp-clean/palace_facade_clean.lsp?raw=true)
- [تحميل AutoCAD DXF](drawings/palace-autolisp-clean/palace_clean_estimated_mm.dxf?raw=true)
- [تحميل PDF بالأبعاد والجدول](drawings/palace-autolisp-clean/palace_clean_estimated_mm.pdf?raw=true)
- [تعليمات التشغيل وحدود الدقة والفحوص](drawings/palace-autolisp-clean/README_AR.md)

التشغيل: **APPLOAD → اختيار LSP → PALACE**. العرض الافتراضي 14000 مم قابل للتغيير. الأبعاد تقديرية، والزخارف إعادة بناء بصرية. الحواف المشتركة مرسومة مرة واحدة، دون نهايات سائبة. كود AutoLISP مفحوص بالمحلل والمحاكاة، ولم يُشغّل داخل AutoCAD هنا.

![الواجهة المنظفة بالأبعاد](drawings/palace-autolisp-clean/palace_clean_preview.png)


## الواجهة الجديدة — خطوط سوداء موحّدة وخلفية بيضاء

- [تحميل الحزمة كاملة ZIP](drawings/palace-uniform/palace_facade_package.zip?raw=true)
- [تحميل AutoCAD DXF](drawings/palace-uniform/palace_facade_uniform.dxf?raw=true)
- [تحميل PDF متجه](drawings/palace-uniform/palace_facade_uniform.pdf?raw=true)
- [معاينة الرسم](drawings/palace-uniform/palace_facade_preview.png)
- [التفاصيل والطبقات وحدود الدقة](drawings/palace-uniform/README_AR.md)

سُمك موحّد **0.18 مم**، وجميع **2023** مسارًا مغلقة. يتضمن DXF مسطحًا أبيض خلف الحدود السوداء. الرسم واجهة بمقياس نسبي، والزخارف إعادة بناء هندسية تقريبية من الصورة.

![معاينة الواجهة بخطوط موحدة](drawings/palace-uniform/palace_facade_preview.png)


## تحميل الواجهة — النسخة الثانية

- [كل الملفات في ZIP](drawings/elevation-v2/elevation_v2_package.zip)
- [رسم AutoCAD DXF بطبقات وأوزان خطوط](drawings/elevation-v2/elevation_v2_lineweights.dxf)
- [رسم PDF متجه](drawings/elevation-v2/elevation_v2.pdf)
- [معاينة PNG](drawings/elevation-v2/elevation_v2_preview.png)
- [تفاصيل المقياس والتحقق](drawings/elevation-v2/README_AR.md)

افتح الملف المطلوب واضغط زر **Download raw file** (علامة السهم لأسفل) لحفظه على جهازك. ويمكن تنزيل المستودع كاملًا من **Code → Download ZIP**.

![معاينة الواجهة](drawings/elevation-v2/elevation_v2_preview.png)

الرسم إعادة بناء بصرية بمقياس نسبي؛ لم يُضبط على أبعاد مساحية. النسخة الثانية تحتوي على 443 خطًا متجهًا، مع فحوص لصحة DXF وPDF واتساق إحداثيات المخرجين. لا تعني هذه الفحوص ضمان المطابقة الكاملة للصورة الأصلية.

## المهارة

[CAD Elevation Vectorizer](.agents/skills/cad-elevation-vectorizer/SKILL.md)
