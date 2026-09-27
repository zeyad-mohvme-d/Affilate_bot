# نظام أتمتة التسويق بالعمولة والنشر متعدد المنصات

> نظام Python لأتمتة اكتشاف المنتجات، إنشاء المحتوى، إدارة الـqueue، والنشر المجدول على Telegram وX وPinterest.

## نظرة عامة

المشروع يحول عملية نشر عروض Amazon إلى pipeline مؤتمتة:

1. البحث عن منتجات من Amazon باستخدام Playwright.
2. استخراج ASIN والاسم والسعر والصورة ومعلومات الخصم.
3. منع التكرار بالاعتماد على سجل المنتجات المنشورة.
4. تخزين المنتجات الجديدة في queue مستمرة.
5. إنشاء كابشن تسويقي عربي باستخدام قوالب متناوبة.
6. إنشاء صورة منتج 1080×1080 وفيديو رأسي قصير 1080×1920.
7. النشر بشكل مستقل على Telegram وX وPinterest.
8. تشغيل الـworkflow تلقائيًا باستخدام GitHub Actions.

> **ملاحظة:** المشروع الحالي ليس تطبيق LLM. توليد الكابشن يعتمد على templates ولا يستدعي LLM API.

## المعمارية

```text
GitHub Actions
      │
      ├── Daily Scrape
      │       │
      │       ▼
      │   Amazon + Playwright
      │       │
      │       ▼
      │   Product Queue
      │       │
      └── Scheduled Post
              │
              ▼
       Content Pipeline
       ├── Arabic Caption
       ├── Product Image
       └── Short Video
              │
       ┌──────┼────────┐
       ▼      ▼        ▼
   Telegram   X    Pinterest
              │
              ▼
        Posted History
```

## أهم المكونات

| المكوّن | الوظيفة |
|---|---|
| `main.py` | Orchestrator لوضعي scrape وpost |
| `scraper/amazon_scraper.py` | scraping واستخراج بيانات المنتجات |
| `content/caption.py` | بناء الكابشن العربي |
| `content/image_builder.py` | إنشاء صور المنتجات |
| `content/video_builder.py` | إنشاء الفيديوهات القصيرة |
| `posters/` | النشر على المنصات الثلاث |
| `state/queue.json` | المنتجات المنتظرة للنشر |
| `state/posted.json` | سجل المنتجات المنشورة |
| `.github/workflows/` | الجدولة والتنفيذ التلقائي |

## التقنيات

Python 3.11 • Playwright • Pillow • MoviePy • python-telegram-bot • GitHub Actions • JSON state management

## الاعتمادية

يتضمن المشروع:

- منع تكرار المنتجات باستخدام ASIN.
- التحقق من البيانات المطلوبة قبل الإضافة للـqueue.
- اكتشاف صفحات CAPTCHA / robot-check.
- حفظ debug artifacts عند فشل scraping.
- محاولة النشر لكل منصة بشكل مستقل.
- الاحتفاظ بالعنصر في queue عند فشل جميع المنصات.
- concurrency control في GitHub Actions لحماية تحديث الـstate.
- إمكانية تشغيل الـworkflows يدويًا.

## الأمان

الأسرار وبيانات الدخول لا يجب أن تكون داخل Git:

- `config.json`
- `x_cookies.json`
- `pinterest_cookies.json`

استخدم GitHub Actions Secrets أو environment variables للقيم الحساسة، واحتفظ بالـaffiliate IDs الفعلية خارج ملفات الـexample العامة.

## التشغيل محليًا

```bash
pip install -r requirements.txt
python -m playwright install chromium

python main.py --scrape
python main.py --post
```

لإعداد التشغيل، أنشئ `config.json` اعتمادًا على `config.example.json` وأضف القيم الحساسة عبر environment variables.

## ملاحظة

Browser automation يعتمد على واجهات المواقع الخارجية، لذلك قد تتطلب selectors وauthenticated sessions صيانة عند تغيّر المنصات.

## الترخيص

MIT
