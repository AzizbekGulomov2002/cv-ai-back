# Sun'iy Intellekt Asosida Rezyumelarni Reytinglash Tizimi Hujjatlari

## Mundarija
1. [Loyiha haqida umumiy ma'lumot](#loyiha-haqida-umumiy-malumot)
2. [Tizim arxitekturasi](#tizim-arxitekturasi)
3. [O'rnatish bo'yicha yo'riqnoma](#ornatish-boyicha-yoriqnoma)
4. [Muhit sozlash](#muhit-sozlash)
5. [API hujjatlari](#api-hujjatlari)
6. [Sun'iy intellekt tushuntirish tizimi](#suniy-intellekt-tushuntirish-tizimi)
7. [Audit yozuvlari](#audit-yozuvlari)
8. [Yevropa Ittifoqi Sun'iy Intellekt Qonuni talablari](#yevropa-ittifoqi-suniy-intellekt-qonuni-talablari)
9. [Inson nazorati](#inson-nazorati)
10. [Noto'g'ri qarashlarni aniqlash](#notogrisi-qarashlarni-aniqlash)

## Loyiha haqida umumiy ma'lumot

Sun'iy Intellekt Asosida Rezyumelarni Reytinglash Tizimi - bu nomzodlarni ish talablariga muvofiq avtomatik ravishda baholash uchun mo'ljallangan Django asosidagi backend dasturi. Bu tizim yuqori xavfli sun'iy intellekt tizimi tamoyillari asosida qurilgan va quyidagilarni ta'minlaydi:

- **Shaffoflik**: Har bir reytinglash qarori uchun batafsil tushuntirishlar
- **Inson nazorati**: Majburiy inson ko'rib chiqishi va qarorni o'zgartirish imkoniyatlari
- **Audit yozuvlari**: Tizimning barcha harakatlarini to'liq yozib borish
- **Noto'g'ri qarashlarni aniqlash**: O'rnatilgan noxush qarashlarni kuzatish va hisobot berish
- **Qonunchilikka muvofiqlik**: Yevropa Ittifoqi Sun'iy Intellekt Qonuni talablariga muvofiqlik

## Tizim arxitekturasi

### Tizim komponentlari

```
ai_cv_system/
├── manage.py                 # Django boshqaruv fayli
├── .env                     # Muhit o'zgaruvchilari
├── config/                  # Django sozlamalari
│   ├── settings.py
│   └── urls.py
├── apps/                    # Django ilovalari
│   ├── users/              # Foydalanuvchilarni boshqarish
│   ├── candidates/         # Nomzodlarni boshqarish
│   ├── jobs/              # Ish e'lonlari boshqaruvi
│   ├── ranking/           # Sun'iy intellekt reytinglash tizimi
│   ├── ai/                # Sun'iy intellekt sozlamalari
│   └── audit/             # Audit yozuvlari
├── services/              # Biznes logika qatami
│   ├── parser_service.py    # Rezyume matnini ajratish
│   ├── embedding_service.py # OpenAI embeddings
│   ├── ranking_service.py   # Nomzodlarni reytinglash
│   ├── explain_service.py   # Sun'iy intellekt tushuntirishlari
│   └── bias_service.py      # Noto'g'ri qarashlarni aniqlash
└── docs/                  # Hujjatlar
```

### Xizmat qatlami arxitekturasi

Tizim xizmat-orientlangan arxitektura asosida qurilgan:
- **Ko'rinishlar (Views)** HTTP so'rovlari va javoblarni boshqaradi
- **Xizmatlar (Services)** biznes logikasini o'z ichiga oladi
- **Modellar (Models)** ma'lumotlarni saqlashni boshqaradi
- **Serializerlar** ma'lumotlarni tekshirish va serializatsiya qilishni amalga oshiradi

## O'rnatish bo'yicha yo'riqnoma

### Zaruriy dasturlar

- Python 3.8 yoki undan yuqori versiya
- pip (Python paket menejeri)
- Virtual muhit (tavsiya etiladi)

### O'rnatish bosqichlari

1. **Loyiha papkasiga o'ting:**
   ```bash
   cd ai_cv_system
   ```

2. **Virtual muhit yarating va faollashtiring:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows uchun: venv\Scripts\activate
   ```

3. **Bog'liqliklarni o'rnating:**
   ```bash
   pip install -r requirements.txt
   ```
   Asosiy ro‘yxat **minimal** (PythonAnywhere disk uchun): Django, DRF, `openai`, `google-generativeai`, `numpy` va lokal PDF kutubxonalari **yo‘q** — embeddinglar `math`/`random` bilan hisoblanadi.  
   Lokal `parser_service` orqali PDF/DOCX dan to‘g‘ridan-to‘g‘ri matn kerak bo‘lsa: `pip install -r requirements-optional.txt`.

4. **Muhit o'zgaruvchilarini sozlang:**
   ```bash
   cp .env.example .env  # Namunadan yarating
   # .env faylini o'z sozlamalaringiz bilan tahrirlang
   ```

5. **Ma'lumotlar bazasi migratsiyalarini ishga tushiring:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Admin foydalanuvchini yarating (ixtiyoriy):**
   ```bash
   python manage.py createsuperuser
   ```

7. **Rivojlanish serverini ishga tushiring:**
   ```bash
   python manage.py runserver
   ```

Dastur `http://127.0.0.1:8000/` manzilida mavjud bo'ladi

## Muhit sozlash

### Majburiy muhit o'zgaruvchilari

Loyiha ildizida `.env` fayli yarating va quyidagi sozlamalarni kiriting:

```env
# OpenAI sozlamalari (Majburiy)
OPENAI_API_KEY=sizning_openai_api_kalitingiz

# Django sozlamalari (Ixtiyoriy)
DEBUG=True
SECRET_KEY=sizning-maxfiy-kalitingiz

# Ma'lumotlar bazasi (Ixtiyoriy - sukut bo'yicha SQLite)
DATABASE_URL=sqlite:///db.sqlite3
```

### OpenAI API kaliti

To'liq sun'iy intellekt funksionalligini olish uchun OpenAI API kaliti kerak:

1. [OpenAI API Platform](https://platform.openai.com/api-keys) ga tashrif buyuring
2. Hisob yarating va API kalitini yarating
3. Uni `.env` fayliga `OPENAI_API_KEY` sifatida qo'shing

**Eslatma**: Agar OpenAI API kaliti berilmagan bo'lsa, tizim namoyish maqsadida dummy embeddings ishlatadi.

## API hujjatlari

### Autentifikatsiya

Barcha API endpoint'lar token asosida autentifikatsiyani talab qiladi.

#### Foydalanuvchini ro'yxatdan o'tkazish
```http
POST /api/auth/register/
Content-Type: application/json

{
  "username": "kadrovchi1",
  "email": "kadrovchi@kompaniya.com",
  "password": "xavfsizparol123",
  "password_confirm": "xavfsizparol123",
  "first_name": "Javohir",
  "last_name": "Aliyev",
  "role": "recruiter",
  "company": "Tech Corp"
}
```

#### Tizimga kirish
```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "kadrovchi1",
  "password": "xavfsizparol123"
}
```

**Javob:**
```json
{
  "message": "Muvaffaqiyatli kirdingiz",
  "user": {
    "id": 1,
    "username": "kadrovchi1",
    "email": "kadrovchi@kompaniya.com",
    "role": "recruiter",
    "company": "Tech Corp"
  },
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

### Nomzodlarni boshqarish

#### Rezyume yuklash
```http
POST /api/candidates/upload/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Content-Type: multipart/form-data

name: Javohir Aliyev
email: javohir.aliyev@email.com
phone: +998901234567
cv_file: [PDF yoki DOCX fayl]
```

#### Nomzodlar ro'yxati
```http
GET /api/candidates/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

# Ixtiyoriy parametrlar:
# ?search=python          # Ism, email, ko'nikmalar bo'yicha qidirish
# ?min_experience=3        # Minimal tajriba bo'yicha filtrlash
# ?skills=python,django    # Ko'nikmalar bo'yicha filtrlash
```

### Ish o'rinlari boshqaruvi

#### Ish e'lonini yaratish
```http
POST /api/jobs/create/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Content-Type: application/json

{
  "title": "Katta Python Dasturchi",
  "company": "Tech Corp",
  "location": "Toshkent, O'zbekiston",
  "description": "Biz tajribali Python dasturchini qidiramiz...",
  "requirements": "5+ yil Python tajribasi, Django, REST API...",
  "job_type": "full_time",
  "level": "senior",
  "required_skills": ["Python", "Django", "REST API", "PostgreSQL"],
  "preferred_skills": ["Docker", "AWS", "React"],
  "min_experience": 5,
  "max_experience": 10,
  "salary_min": 3000,
  "salary_max": 5000,
  "currency": "USD"
}
```

### Sun'iy intellekt reytinglash tizimi

#### Reytinglashni boshlash
```http
POST /api/ranking/run/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Content-Type: application/json

{
  "job_id": 1,
  "candidate_ids": [1, 2, 3, 4, 5],  # Ixtiyoriy
  "notes": "Katta dasturchi lavozimi uchun dastlabki saralash"
}
```

#### Inson tomonidan qarorni o'zgartirish
```http
POST /api/ranking/1/override/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Content-Type: application/json

{
  "human_decision": "accepted",
  "human_score": 95.0,
  "human_feedback": "Kuchli texnik ko'nikmalar va madaniy moslashuvchanlik"
}
```

## Sun'iy intellekt tushuntirish tizimi

Tizim har bir reytinglash qarori uchun batafsil tushuntirishlar beradi.

### Tushuntirish komponentlari

1. **Mos keluvchi ko'nikmalar**: Rezyume va ish talablarida topilgan ko'nikmalar
2. **Yetishmayotgan ko'nikmalar**: Talab qilingan lekin nomzodda yo'q ko'nikmalar
3. **Tajriba tahlili**: Nomzodning tajribasi va ish talablari taqqoslash
4. **Ta'lim baholash**: Ta'lim fonini baholash
5. **Umumiy ball tushuntirish**: Raqamli ballning inson tushunadigan talqini

### Ball kategoriyalari

- **90-100**: Mukammal mos - ish talablariga to'liq mos keladi
- **80-89**: Juda yaxshi - ko'pchilik talablarni qondiradi
- **70-79**: Yaxshi - asosiy talablarni qondiradi, ozgina kamchiliklar bor
- **60-69**: O'rtacha - tegishli tajriba bor, ba'zi kamchiliklar mavjud
- **40-59**: Qisman mos - ba'zi tegishli ko'nikmalar, sezilarli kamchiliklar
- **0-39**: Past - ish talablariga yomon mos keladi

## Audit yozuvlari

### To'liq yozib borish

Tizim barcha harakatlarni yozib boradi:

- **Foydalanuvchi harakatlari**: Kirish, chiqish, profil yangilanishi
- **Rezyume operatsiyalari**: Yuklash, tahlil qilish, embedding yaratish
- **Ish boshqaruvi**: Yaratish, yangilash, o'chirish
- **Sun'iy intellekt operatsiyalari**: Reytinglash, tushuntirish yaratish
- **Inson qarorlari**: O'zgartirishlar, ko'rib chiqishlar, fikr-mulohazalar

### Yozuv tuzilishi

```json
{
  "id": 123,
  "user": "kadrovchi1",
  "action_type": "ranking",
  "action_description": "Katta Python Dasturchi uchun 5 nomzod bilan reytinglash amalga oshirildi",
  "risk_level": "high",
  "timestamp": "2024-03-15T10:30:00Z",
  "success": true,
  "ai_confidence": 85.0,
  "metadata": {
    "job_id": 1,
    "candidates_count": 5
  }
}
```

## Yevropa Ittifoqi Sun'iy Intellekt Qonuni talablari

Bu tizim yuqori xavfli sun'iy intellekt tizimlari uchun majburiy talablarni amalga oshiradi:

### Amalga oshirilgan majburiy talablar

1. **Inson nazorati** (14-modda)
   - Barcha reytinglash qarorlari uchun inson ko'rib chiqishi talab qilinadi
   - Operatorlar uchun qarorni bekor qilish imkoniyatlari
   - Aniq ko'tarish tartib-taomillari

2. **Shaffoflik** (13-modda)
   - Barcha sun'iy intellekt qarorlari uchun batafsil tushuntirishlar
   - Sun'iy intellekt ishlatilganda aniq ko'rsatish
   - Tizim imkoniyatlari va cheklovlarini foydalanuvchi tushunishi

3. **Aniqlik va mustahkamlik** (15-modda)
   - Zaxira mexanizmlar (OpenAI mavjud bo'lmaganda dummy embeddings)
   - Xatoliklarni boshqarish va yumshoq degradatsiya
   - Ishlash monitoringi va analitika

4. **Ma'lumotlar boshqaruvi** (10-modda)
   - Keng qamrovli audit yozuvi
   - Ma'lumotlar sifatini tekshirish
   - Noto'g'ri qarashlarni kuzatish va aniqlash

## Inson nazorati

### Majburiy inson ko'rib chiqishi

Barcha sun'iy intellekt reytinglash qarorlari inson nazoratini talab qiladi:

1. **Dastlabki ko'rib chiqish**: Inson kadrovchi sun'iy intellekt reytinglarini ko'rib chiqadi
2. **Qarorni bekor qilish**: Odamlar sun'iy intellekt qarorlarini bekor qila oladi
3. **Fikr-mulohaza yig'ish**: Tizim inson fikr-mulohazalarini yozib oladi
4. **Ta'lim sikli**: Inson qarorlari tizim yaxshilanishiga yordam beradi

### Qaror kategoriyalari

- **Qabul qilindi**: Nomzod keyingi bosqichga o'tadi
- **Rad etildi**: Nomzod mos emas
- **Qisqa ro'yxat**: Nomzod qo'shimcha baholash kerak
- **Kutilmoqda**: Inson ko'rib chiqishi kutilmoqda

## Noto'g'ri qarashlarni aniqlash

### Avtomatik noto'g'ri qarashlarni kuzatish

Tizim doimiy ravishda potentsial noto'g'ri qarashlarni kuzatadi:

### Kuzatiladigan himoyalangan xususiyatlar

1. **Jins**: Rezumeda jinsga oid atamalarni aniqlash
2. **Yosh**: Yosh ko'rsatkichlarini aniqlash
3. **Millat**: ASCII bo'lmagan ismlarni aniqlash
4. **Din**: Diniy mansubligi eslatmalari
5. **Oila holati**: Nikoh holati, oila havolalari
6. **Ta'lim**: Elita ta'lim muassasalari tarafkashligi
7. **Ijtimoiy-iqtisodiy**: Qimmat hududlar ko'rsatkichlari

### Tarafkashlik bayroqlari

Potentsial tarafkashlik ko'rsatkichlari aniqlanganda tizim:

1. **Reytingni belgilaydi** aniq tarafkashlik turlari bilan
2. **Aniqlanishni yozib qo'yadi** audit maqsadlari uchun
3. **Inson ko'rib chiquvchilarni ogohlantiradi** potentsial muammolar haqida
4. **Bir nechta reytinglar bo'ylab naqshlarni kuzatadi**

## Eng yaxshi amaliyotlar

### Administratorlar uchun

1. **Muntazam kuzatuv**: Haftalik audit yozuvlari va tarafkashlik hisobotlarini tekshiring
2. **Inson ta'limi**: Barcha inson ko'rib chiquvchilar tarafkashlik xavflarini tushunishga ishonch hosil qiling
3. **Tizim yangilanishi**: Tarafkashlik aniqlash naqshlarini joriy saqlang
4. **Muvofiqlik ko'rib chiqishlari**: Muntazam Yevropa Ittifoqi Sun'iy Intellekt Qonuni muvofiqlik auditlarini o'tkazing

### Kadrovchilar uchun

1. **Barcha reytinglarni ko'rib chiqing**: Faqat sun'iy intellekt balllariga tayanmang
2. **Qarorlarni hujjatlang**: O'zgartirishlar uchun batafsil fikr-mulohaza bering
3. **Tarafkashligi kuzating**: Potentsial tarafkashlik ko'rsatkichlariga ehtiyotkor bo'ling
4. **Doimiy ta'lim**: Adolatli ish berish amaliyotlari bo'yicha yangilanib turing

## Muammolarni bartaraf etish

### Keng tarqalgan muammolar

1. **OpenAI API xatolari**
   - API kalitining yaroqliligini tekshiring
   - Tezlik cheklovlari oshmasligini tekshiring
   - Tizim dummy embeddingslarga qaytadi

2. **Rezyume tahlil etish muvaffaqiyatsizligi**
   - Fayl formati qo'llab-quvvatlanishini ta'minlang (PDF/DOCX)
   - Fayl o'lchami cheklovlarini tekshiring (10MB)
   - Fayl buzilmaganligini tekshiring

3. **Yomon reytinglash sifati**
   - Ish tavsifi sifatini ko'rib chiqing
   - Ko'nikmalar kalit so'zlari aniqligini tekshiring
   - Nomzod rezyume to'liqligini tekshiring

---

*Bu hujjat shaffoflik, inson nazorati va qonunchilik talablariga muvofiqlikni talab qiladigan yuqori xavfli dasturlar uchun mo'ljallangan sun'iy intellekt tizimining bir qismidir.*