"""
VIBE engine - offline, free, Persian + English.

Input can be:
  * a vibe sentence that exists in the library        -> case 1 (exact)
  * a vibe sentence similar to a library vibe         -> case 2 (similar)
  * a vibe sentence that is NOT in the library        -> case 3 (estimate the 10 axis numbers
                                                         from the nearest library vibes)
  * a perfume name ("aventus", "ساواج دیور")          -> its vibes + similar perfumes

Backends (set automatically):
  1. sentence-transformers multilingual model (understands Persian natively, free, runs offline
     after one-time download):  paraphrase-multilingual-MiniLM-L12-v2
  2. fallback: TF-IDF + a built-in Persian->English glossary (works with only pandas/sklearn)

Usage:
    python vibe_engine.py "ghorub kenar darya"            (any text)
    python vibe_engine.py "غروب کنار دریا"
    python vibe_engine.py "aventus"
or in Python:
    from vibe_engine import Engine; e = Engine('VIBE_final_v25.xlsx'); print(e.recommend('بوی بارون'))
"""
import re, sys, difflib, unicodedata
import numpy as np, pandas as pd

AX = ['Thermal', 'Freshness', 'Sweetness', 'Dryness', 'Texture', 'Light-Dark', 'Energy',
      'Intensity', 'Natural-Urban', 'Woody-Earthy', 'Floral', 'Fruity', 'Smoky-Spicy']
INACTIVE = ('Energy', 'Light-Dark')            # kept in the file, ignored in ranking
AX_FA = {'Thermal': 'گرمی', 'Freshness': 'طراوت', 'Sweetness': 'شیرینی', 'Dryness': 'خشکی',
         'Texture': 'بافت', 'Intensity': 'شدت', 'Natural-Urban': 'طبیعی-شهری',
         'Woody-Earthy': 'چوبی-خاکی', 'Floral': 'گلی', 'Fruity': 'میوه‌ای', 'Smoky-Spicy': 'دودی-ادویه‌ای'}
MODEL = 'sentence-transformers/all-MiniLM-L6-v2'   # English-only MVP (small, fast, offline after first download)

# thresholds on cosine similarity (text -> vibe). TF-IDF values come from the 68-phrase test.
# !! CALIBRATE the 'st' values with match_test.py and real phrases when the model is available !!
THR = {'tfidf': {'case2': 0.20, 'case3_floor': 0.12},
       'st':    {'case2': 0.55, 'case3_floor': 0.25}}

# ---------------------------------------------------------------- Persian helpers
def norm_fa(s):
    s = str(s).lower()
    s = s.replace('ي', 'ی').replace('ك', 'ک').replace('‌', ' ').replace('ۀ', 'ه').replace('ة', 'ه')
    s = re.sub('[ً-ٟـ]', '', s)                       # harakat, kashida
    s = s.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
    s = re.sub(r"[^\w\s&']", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def is_fa(s): return bool(re.search('[؀-ۿ]', str(s)))

# Persian word -> English (feeds the TF-IDF fallback; the multilingual model does not need it)
GLOSS = {
 # nature / places
 'غروب': 'sunset', 'غروب آفتاب': 'sunset', 'طلوع': 'sunrise dawn', 'سحر': 'dawn', 'صبح': 'morning', 'ظهر': 'noon',
 'عصر': 'afternoon', 'شب': 'night', 'نیمه شب': 'midnight', 'شبانه': 'night', 'شام': 'dinner', 'ساحل': 'coast beach',
 'دریا': 'sea', 'اقیانوس': 'ocean', 'ساحلی': 'coastal', 'ماسه': 'sand', 'شن': 'sand', 'جزیره': 'island', 'گرمسیری': 'tropical',
 'استخر': 'swimming pool', 'دریاچه': 'lake', 'رودخانه': 'river', 'آبشار': 'waterfall', 'کوه': 'mountain', 'کوهستان': 'mountain',
 'کلبه': 'cabin', 'جنگل': 'forest', 'درخت': 'tree woods', 'چوب': 'wood', 'چمن': 'meadow grass', 'مزرعه': 'fields',
 'باغ': 'garden', 'گلخانه': 'greenhouse', 'گل': 'flower', 'گل رز': 'rose', 'رز': 'rose', 'یاس': 'jasmine', 'اسطوخودوس': 'lavender',
 'بنفشه': 'violet', 'نرگس': 'narcissus', 'شکوفه': 'blossom', 'بهار': 'spring', 'تابستان': 'summer', 'پاییز': 'autumn',
 'زمستان': 'winter', 'برف': 'snow', 'برفی': 'snowy', 'یخ': 'ice', 'سرد': 'cold', 'خنک': 'cool', 'گرم': 'warm', 'داغ': 'hot',
 'آفتاب': 'sun sunny', 'آفتابی': 'sunny', 'خورشید': 'sun', 'ماه': 'moon', 'ستاره': 'stars', 'آسمان': 'sky', 'ابر': 'cloud',
 'باران': 'rain', 'بارون': 'rain', 'بارانی': 'rainy', 'بعد از باران': 'after the rain', 'خاک': 'earth soil', 'خاک نم': 'wet earth',
 'نم': 'damp', 'مه': 'fog mist', 'باد': 'wind breeze', 'نسیم': 'breeze', 'صحرا': 'desert', 'کویر': 'desert', 'بیابان': 'desert',
 'غار': 'cave', 'سنگ': 'stone', 'آتش': 'fire', 'شومینه': 'fireplace', 'آتیش': 'fire', 'دود': 'smoke', 'دودی': 'smoky',
 # cities / places / things
 'شهر': 'city', 'شهری': 'urban', 'خیابان': 'street', 'کافه': 'cafe', 'قهوه': 'coffee', 'قهوه خانه': 'cafe', 'چای': 'tea', 'شکلات': 'chocolate',
 'کاکائو': 'cocoa', 'نان': 'bread', 'کیک': 'cake', 'شیرینی': 'sweet pastry', 'عسل': 'honey', 'وانیل': 'vanilla', 'کارامل': 'caramel',
 'میوه': 'fruit', 'توت فرنگی': 'strawberry', 'توت': 'berry', 'پرتقال': 'orange', 'لیمو': 'lemon', 'هلو': 'peach', 'سیب': 'apple',
 'گیلاس': 'cherry', 'انجیر': 'fig', 'نارگیل': 'coconut', 'نعنا': 'mint', 'خیار': 'cucumber', 'آب': 'water', 'آب خنک': 'cold water',
 'نوشیدنی': 'drink', 'بار': 'bar', 'کتاب': 'book', 'کتابخانه': 'library books', 'کاغذ': 'paper', 'قلم': 'pen', 'نقاشی': 'painting art',
 'گالری': 'gallery', 'موزه': 'museum', 'موسیقی': 'music', 'جاز': 'jazz', 'رقص': 'dancing', 'سینما': 'cinema', 'فیلم': 'movie cinematic',
 'هتل': 'hotel', 'لوکس': 'luxury', 'مجلل': 'luxurious opulent', 'پشت بام': 'rooftop', 'نئون': 'neon', 'توکیو': 'tokyo', 'پاریس': 'paris',
 'لندن': 'london', 'نیویورک': 'new york', 'فلورانس': 'florence', 'ایتالیا': 'italy', 'یونان': 'greece', 'دبی': 'dubai',
 'ماشین': 'car', 'جاده': 'road', 'قطار': 'train', 'هواپیما': 'plane', 'سفر': 'trip travel', 'تعطیلات': 'holiday vacation',
 'خانه': 'home', 'خونه': 'home', 'آپارتمان': 'apartment', 'تخت': 'bed', 'پتو': 'blanket', 'رخت': 'laundry', 'لباس شسته': 'clean laundry',
 'لباس': 'clothes', 'پیراهن': 'shirt', 'کت': 'coat', 'چرم': 'leather', 'کیف': 'bag', 'ژاکت': 'jacket', 'کتان': 'linen', 'مخمل': 'velvet',
 'ابریشم': 'silk', 'ژاکت چرم': 'leather jacket', 'جواهر': 'jewelry', 'طلا': 'gold golden', 'طلایی': 'golden', 'نقره': 'silver',
 'سیاه': 'black', 'مشکی': 'black', 'سفید': 'white', 'قرمز': 'red', 'آبی': 'blue', 'سبز': 'green', 'زرد': 'yellow', 'صورتی': 'pink',
 'بنفش': 'purple', 'نارنجی': 'orange', 'قهوه ای': 'brown', 'خاکستری': 'grey',
 'سیگار': 'cigarette', 'تنباکو': 'tobacco', 'پیپ': 'pipe tobacco', 'عود': 'oud', 'عنبر': 'amber', 'مشک': 'musk', 'صندل': 'sandalwood',
 'زعفران': 'saffron', 'هل': 'cardamom', 'ادویه': 'spice', 'فلفل': 'pepper', 'نمک': 'salt', 'مرکبات': 'citrus',
 'بچه': 'baby', 'نوزاد': 'newborn baby', 'مادر': 'mother', 'آغوش': 'hug', 'بغل': 'hug', 'بوسه': 'kiss', 'عشق': 'love', 'عاشقانه': 'romantic',
 'قرار': 'date', 'نامه': 'letter', 'نامه عاشقانه': 'love letter', 'شمع': 'candle', 'شام عاشقانه': 'candlelit dinner', 'چتر': 'umbrella',
 'ورزش': 'sport gym', 'دویدن': 'running', 'باشگاه': 'gym', 'یوگا': 'yoga', 'اسپا': 'spa', 'حمام': 'bath', 'پیاده روی': 'walking',
 'کلاس': 'classroom', 'مدرسه': 'school', 'دانشگاه': 'university', 'بیمارستان': 'hospital', 'دندانپزشکی': 'dentist', 'ماشین جدید': 'new car',
 'عروسی': 'wedding', 'تولد': 'birthday', 'مهمانی': 'party', 'جشن': 'celebration', 'کریسمس': 'christmas', 'نوروز': 'spring new year',
 'کار': 'work', 'دفتر': 'office', 'شغل': 'work', 'بازی': 'game', 'بازی ویدیویی': 'video games',
 # moods
 'آرام': 'calm', 'آرامش': 'calm peaceful', 'ساکت': 'quiet', 'سکوت': 'silence quiet', 'تنهایی': 'solitude alone', 'خلوت': 'private quiet',
 'شاد': 'joyful cheerful', 'شادی': 'joy', 'خوشحال': 'happy', 'انرژی': 'energy', 'پرانرژی': 'energetic', 'سرزنده': 'lively', 'تازه': 'fresh',
 'تمیز': 'clean', 'پاک': 'pure clean', 'خالص': 'pure', 'شفاف': 'clear', 'سبک': 'light', 'سنگین': 'heavy', 'غلیظ': 'rich intense',
 'قوی': 'strong powerful', 'قدرت': 'power', 'مرموز': 'mysterious', 'رازآلود': 'mysterious secretive', 'تاریک': 'dark', 'تاریکی': 'dark',
 'روشن': 'bright', 'نور': 'light', 'گرم و صمیمی': 'warm cozy', 'صمیمی': 'intimate cozy', 'دنج': 'cozy', 'نوستالژی': 'nostalgic',
 'خاطره': 'memory nostalgic', 'نوستالژیک': 'nostalgic', 'غمگین': 'melancholic', 'دلتنگی': 'longing melancholic', 'رویایی': 'dreamy',
 'خیال': 'dreamy', 'رمانتیک': 'romantic', 'جذاب': 'magnetic charming', 'اغواگر': 'seductive', 'حسی': 'sensual', 'شیک': 'elegant chic',
 'ظریف': 'delicate elegant', 'کلاسیک': 'classic', 'مدرن': 'modern', 'آینده': 'futuristic', 'مینیمال': 'minimal', 'ساده': 'simple minimal',
 'اعتماد به نفس': 'confident', 'جسور': 'bold', 'یاغی': 'rebellious', 'سرکش': 'rebellious', 'ماجراجو': 'adventurous', 'آزاد': 'free',
 'بی خیال': 'carefree', 'راحت': 'relaxed casual', 'خسته': 'tired', 'خواب': 'sleep sleepy', 'خواب آلود': 'sleepy', 'تمرکز': 'focused',
 'خلاق': 'creative', 'هنری': 'artistic', 'روشنفکر': 'intellectual', 'مغرور': 'proud', 'لوند': 'playful', 'بازیگوش': 'playful',
 'معصوم': 'innocent', 'کودکانه': 'childlike playful', 'ملایم': 'gentle soft', 'نرم': 'soft smooth', 'لطیف': 'tender delicate',
 'سرد و تمیز': 'cool clean', 'شیرین': 'sweet', 'تلخ': 'bitter', 'ترش': 'sour tart', 'تند': 'spicy sharp', 'خشک': 'dry', 'مرطوب': 'humid',
 'چوبی': 'woody', 'خاکی': 'earthy', 'گلی': 'floral', 'میوه ای': 'fruity', 'سبزه': 'green', 'گیاهی': 'herbal green', 'طبیعی': 'natural',
 'عطر': 'perfume', 'بو': 'smell scent', 'بوی': 'smell of', 'حس': 'feeling', 'حال و هوا': 'mood vibe', 'فضا': 'atmosphere',
 'اولین': 'first', 'آخرین': 'last', 'قدیمی': 'old vintage', 'جدید': 'new', 'کهنه': 'old', 'بهشت': 'paradise', 'خنکی': 'coolness',
}
GLOSS = {norm_fa(k): v for k, v in GLOSS.items()}
STOP_FA = set(norm_fa(x) for x in 'از در به با و یا که را این آن یک من تو ما شما برای مثل مثل وقتی تا بر هم روی توی تو کنار مثل بعد قبل بی'.split())

def fa_to_en(text):
    """longest-match Persian -> English; unknown words are dropped (fallback backend only)."""
    t = norm_fa(text).split(); out = []; i = 0
    while i < len(t):
        for n in (3, 2, 1):
            k = ' '.join(t[i:i + n])
            if k in GLOSS: out.append(GLOSS[k]); i += n; break
            kk = re.sub(r'(ها|های|ای|ی|ان)$', '', k)         # plural / ezafe / ya
            if kk in GLOSS and len(kk) > 1: out.append(GLOSS[kk]); i += n; break
        else:
            i += 1
    return ' '.join(out)

# Persian brand / perfume spellings -> English (used when the user types a perfume in Persian)
BRAND_FA = {'دیور': 'dior', 'شنل': 'chanel', 'شانل': 'chanel', 'کریرد': 'creed', 'کرید': 'creed', 'تام فورد': 'tom ford', 'تامفورد': 'tom ford',
 'ایو سن لورن': 'ysl', 'ایو سنت لورن': 'ysl', 'وای اس ال': 'ysl', 'ورساچه': 'versace', 'ورزاچه': 'versace', 'ارمانی': 'armani',
 'جورجیو آرمانی': 'giorgio armani', 'آرمانی': 'armani', 'امپریو آرمانی': 'emporio armani', 'هرمس': 'hermes', 'پرادا': 'prada',
 'بولگاری': 'bvlgari', 'گرلن': 'guerlain', 'لانکوم': 'lancome', 'لنکوم': 'lancome', 'ژان پل گوتیه': 'jean paul gaultier', 'گوتیه': 'jean paul gaultier',
 'پاکو رابان': 'rabanne', 'رابان': 'rabanne', 'دولچه گابانا': 'dolce & gabbana', 'دولچه اند گابانا': 'dolce & gabbana', 'دولچه': 'dolce & gabbana',
 'هوگو باس': 'hugo boss', 'باس': 'hugo boss', 'باربری': 'burberry', 'بربری': 'burberry', 'والنتینو': 'valentino', 'جو مالون': 'jo malone',
 'جومالون': 'jo malone', 'لو لابو': 'le labo', 'مارلی': 'parfums de marly', 'پارفومز دو مارلی': 'parfums de marly', 'اموج': 'amouage', 'آمواج': 'amouage',
 'زرجف': 'xerjoff', 'زرژف': 'xerjoff', 'مونتال': 'montale', 'ناسوماتو': 'nasomatto', 'لطافه': 'lattafa', 'لتافا': 'lattafa', 'الحرمین': 'al haramain',
 'رصاصی': 'rasasi', 'افنان': 'afnan', 'ارماف': 'armaf', 'کایالی': 'kayali', 'کیلیان': 'by kilian', 'بای کیلیان': 'by kilian', 'مارجیلا': 'maison margiela',
 'میزون مارجیلا': 'maison margiela', 'لویی ویتون': 'louis vuitton', 'ویتون': 'louis vuitton', 'کارولینا هررا': 'carolina herrera', 'ویکتور اند رولف': 'viktor & rolf',
 'نارسیسو رودریگز': 'narciso rodriguez', 'آریانا گراند': 'ariana grande', 'ام اف کی': 'mfk', 'اینیشیو': 'initio'}
PERF_FA = {'ساواژ': 'sauvage', 'سواژ': 'sauvage', 'ساواج': 'sauvage', 'سووژ': 'sauvage', 'ساوج': 'sauvage', 'اونتوس': 'aventus', 'اوانتوس': 'aventus', 'آونتوس': 'aventus', 'لیبره': 'libre',
 'بلو دو شنل': 'bleu de chanel', 'بلو شنل': 'bleu de chanel', 'کوکو مادمازل': 'coco mademoiselle', 'مادمازل': 'coco mademoiselle', 'شنس': 'chance',
 'ژادور': 'j\'adore', 'جادور': 'j\'adore', 'میس دیور': 'miss dior', 'لایت بلو': 'light blue', 'لایت بلو': 'light blue', 'ارس': 'eros', 'اروس': 'eros',
 'بلک اپیوم': 'black opium', 'بلک اوپیوم': 'black opium', 'لاویه است بل': 'la vie est belle', 'لا ویه است بل': 'la vie est belle', 'گود گرل': 'good girl',
 'اسپایس بمب': 'spicebomb', 'فلاور بمب': 'flowerbomb', 'استرانگر ویت یو': 'stronger with you', 'اینویکتوس': 'invictus', 'بکارات': 'baccarat rouge 540',
 'باکارات': 'baccarat rouge 540', 'باکارات رژ': 'baccarat rouge 540', 'سانتال 33': 'santal 33', 'عود وود': 'oud wood', 'تاباکو وانیل': 'tobacco vanille',
 'توسکان لدر': 'tuscan leather', 'لاست چری': 'lost cherry', 'نرولی پورتوفینو': 'neroli portofino', 'دلینا': 'delina', 'لیتون': 'layton', 'پگاسوس': 'pegasus',
 'خمره': 'khamrah', 'خمرا': 'khamrah', 'ترد هرمس': 'terre d\'hermes', 'تر دو هرمس': 'terre d\'hermes', 'فارنهایت': 'fahrenheit', 'اپیوم': 'opium',
 'انجلز شیر': 'angels\' share', 'ماي وی': 'my way', 'مای وی': 'my way', 'وای': 'y', 'آکوا دی جیو': 'acqua di gio', 'آکوا دی جو': 'acqua di gio',
 'گرین ایریش تویید': 'green irish tweed', 'اینترلود': 'interlude man', 'لا نویت': 'la nuit de l\'homme', 'ژنتلمن': 'gentleman', 'ام وای اس ال اف': 'myslf'}
ALIAS_FA = {norm_fa(k): v for k, v in {**BRAND_FA, **PERF_FA}.items()}

def fa_perfume_to_en(q):
    q = norm_fa(q)
    for k in sorted(ALIAS_FA, key=len, reverse=True):
        if re.search(r'(?<!\w)' + re.escape(k) + r'(?!\w)', q): q = re.sub(r'(?<!\w)' + re.escape(k) + r'(?!\w)', ' ' + ALIAS_FA[k] + ' ', q)
    return re.sub(r'\s+', ' ', q).strip()

def strip_acc(s): return ''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c))

def norm_en(s):
    s = str(s).lower().replace('é', 'e').replace('è', 'e').replace('ï', 'i').replace('ô', 'o').replace('ò', 'o').replace('î', 'i').replace('û', 'u').replace('ë', 'e').replace('à', 'a').replace('ç', 'c').replace('°', ' ').replace('ò', 'o')
    s = re.sub(r"[^a-z0-9&' ]", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

COMMON = set('about after again along around before behind below beside between could every first great heart might never night other place quiet right should small smell still their there these thing think those three under until where which while whole would young'.split())
STOP = {'le', 'la', 'l', 'the', 'eau', 'acqua', 'pour', 'les', 'un', 'my', 'black', 'light', 'sauvage'}
def fam(b, n):
    w = re.findall(r"[a-zà-ÿ0-9]+", n.lower()); k = w[0] if w else n
    if k in STOP and len(w) > 1: k = ' '.join(w[:2])
    return b + '|' + k

# ---------------------------------------------------------------- engine
class Engine:
    def __init__(self, xlsx='VIBE_final_v25.xlsx', backend='auto'):
        self.p = pd.read_excel(xlsx, sheet_name='perfumes').reset_index(drop=True)
        self.v = pd.read_excel(xlsx, sheet_name='vibes').reset_index(drop=True)
        p, v = self.p, self.v
        self.V = p[[a + ' Value' for a in AX]].values.astype(float)
        self.T = v[[a + ' Target' for a in AX]].values.astype(float)
        self.W = v[[a + ' Weight' for a in AX]].values.astype(float)
        for a in INACTIVE: self.W[:, AX.index(a)] = 0
        self.lab = [f"{n} ({b})" for b, n in zip(p.Brand, p.Name)]
        self.fams = [fam(b, n) for b, n in zip(p.Brand, p.Name)]
        self.tags = [{t for t in str(s).replace(' ', '').split(',') if t.isdigit()} for s in p.Vibe.fillna('')]
        self.vid = [str(int(i)) for i in v.ID]
        self.doc = (v['Vibe Title'] + '. ' + v['Mood Keywords'].fillna('') + '. ' + v['Sensory Description'].fillna('')).tolist()
        self.doc_plain = [strip_acc(d) for d in self.doc]
        self.title_n = [norm_en(t) for t in v['Vibe Title']]
        self.kw = [{norm_en(k) for k in str(s).split(',') if k.strip()} for s in v['Mood Keywords'].fillna('')]
        self.pname = [norm_en(n) for n in p.Name]
        self.pfull = [norm_en(b + ' ' + n) for b, n in zip(p.Brand, p.Name)]
        self.vstory = {int(i): str(t) for i, t in zip(v.ID, v.Story.fillna(''))}
        self.vtitle = {int(i): str(t) for i, t in zip(v.ID, v['Vibe Title'])}
        self._mask = np.ones(len(p), bool)
        self.tr = {}                                                  # English text -> Persian text (only if the FA columns exist in the workbook)
        for df, pairs in ((v, [('Vibe Title', 'Vibe Title FA'), ('Story', 'Story FA')]), (p, [('Perfume Story', 'Perfume Story FA')])):
            for en, fa_ in pairs:
                if en in df.columns and fa_ in df.columns:
                    for a_, b_ in zip(df[en], df[fa_]):
                        if isinstance(a_, str) and isinstance(b_, str) and b_.strip(): self.tr[a_.strip()] = b_.strip()
        words = ' '.join(self.doc + p.Notes.fillna('').tolist() + p.Accords.fillna('').tolist() + v.Story.fillna('').tolist()
                         + v['Scent Hints (notes / accords)'].fillna('').tolist() + p.Name.tolist() + p.Brand.tolist())
        self.vocab = set(re.findall(r"[a-z]{3,}", norm_en(words)))                # every word the library knows
        self.name_vocab = set(re.findall(r"[a-z0-9]{3,}", ' '.join(self.pfull)))   # perfume + brand tokens
        self.backend = None
        if backend in ('auto', 'st'):
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(MODEL); self.backend = 'st'
                self.D = self.model.encode(self.doc, normalize_embeddings=True)
            except Exception as e:
                if backend == 'st': raise
                print('[engine] multilingual model not available -> TF-IDF fallback:', type(e).__name__)
        if self.backend is None:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.preprocessing import normalize
            from scipy.sparse import hstack
            self._w = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), sublinear_tf=True).fit(self.doc_plain)
            self._c = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True).fit(self.doc_plain)
            self._emb = lambda xs: normalize(hstack([self._w.transform(xs) * 0.6, self._c.transform(xs) * 0.4]).tocsr())
            self._wemb = lambda xs: normalize(self._w.transform(xs))
            self.D = self._emb(self.doc_plain); self.DW = self._wemb(self.doc_plain); self.backend = 'tfidf'
        self.thr = THR[self.backend]

    # ---- text -> similarity to every vibe
    def _sims(self, text):
        if self.backend == 'st':
            return self.D @ self.model.encode([text], normalize_embeddings=True)[0]
        t = strip_acc(fa_to_en(text) if is_fa(text) else text)
        self._last_word = (self._wemb([t]) @ self.DW.T).toarray()[0]          # word-level overlap guard
        return (self._emb([t]) @ self.D.T).toarray()[0]

    # ---- ranking from a 12-number target + weights
    def rank_target(self, T, W, bonus=None, exclude=None, k=3):
        W = np.array(W, float).copy()
        for a in INACTIVE: W[AX.index(a)] = 0
        d = np.abs(T - self.V); sw = W.sum()
        s2 = 1 - (W * d ** 2).sum(1) / (25 * sw); sim = 1 - (W * d).sum(1) / (5 * sw)
        sc = (s2 - s2.mean()) / (s2.std() or 1) - 0.8 * ((W >= 3) & (d >= 3)).sum(1)
        if bonus:
            sc = sc + np.array([sum(w for vid, w in bonus.items() if vid in t) for t in self.tags])
        out, used = [], set(exclude or [])
        for i in np.argsort(-sc):
            if not self._mask[i] or self.fams[i] in used: continue
            out.append((int(i), float(sim[i]))); used.add(self.fams[i])
            if len(out) == k: break
        return out

    def _why(self, i, T, W, fa=False):
        """short reason: the 3 heaviest axes where the perfume is closest to the target"""
        W = np.array(W, float).copy()
        for a in INACTIVE: W[AX.index(a)] = 0
        idx = [j for j in np.argsort(-W) if W[j] > 0][:4]
        idx = sorted(idx, key=lambda j: abs(T[j] - self.V[i, j]))[:3]
        parts = [f"{(AX_FA.get(AX[j]) if fa else AX[j])} {int(self.V[i, j])}/5" for j in idx]
        return ('نزدیک به حال‌وهوا در: ' if fa else 'close on: ') + ', '.join(parts)

    def card(self, i):
        """everything the UI needs to present one perfume"""
        r = self.p.iloc[i]
        yr = r.get('Year')
        if pd.isna(yr):
            m = re.search(r'(19|20)\d\d', str(r.get('Version', ''))); yr = int(m.group()) if m else None
        else: yr = int(yr)
        return {'brand': r.Brand, 'name': r.Name, 'concentration': r.Concentration, 'year': yr, 'gender': r.Gender,
                'segment': r.Segment, 'notes': r.Notes, 'accords': r.Accords, 'story': r.get('Perfume Story') if isinstance(r.get('Perfume Story'), str) and r.get('Perfume Story').strip() else r.get('Vibe Story', ''),
                'stories': self._stories(i), 'axes': {a: float(self.V[i, k]) for k, a in enumerate(AX)}}

    def _stories(self, i):
        """[(vibe title, story)] of this perfume: its primary story first, then the stories of its other vibe tags"""
        out, seen = [], set()
        own = self.p.iloc[i].get('Perfume Story')
        if isinstance(own, str) and own.strip(): out.append(('', own.strip())); seen.add(own.strip())     # the perfume's own story first
        first = str(self.p.iloc[i].get('Vibe Story', '')).strip()
        if first and first not in seen: out.append((str(self.p.iloc[i].get('Vibe', '')).split(' ', 1)[-1], first)); seen.add(first)
        for t in sorted(self.tags[i], key=int):
            if t in self.vid:
                st_ = str(self.v.at[self.vid.index(t), 'Story']).strip()
                if st_ and st_ not in seen: out.append((str(self.v.at[self.vid.index(t), 'Vibe Title']), st_)); seen.add(st_)
        return out

    def _perf(self, rows, T, W, fa):
        return [{'perfume': self.lab[i], 'similarity': round(s, 2), 'why': self._why(i, T, W, fa),
                 'notes': self.p.at[i, 'Notes'], **self.card(i)} for i, s in rows]

    # ---- perfume lookup (English or Persian)
    def find_perfume(self, q):
        qe = norm_en(fa_perfume_to_en(q) if is_fa(q) else q)
        if not qe: return None
        best, bs = None, 0
        for i, (n, f) in enumerate(zip(self.pname, self.pfull)):
            if re.search(r'(?<![a-z0-9])' + re.escape(n) + r'(?![a-z0-9])', qe) or re.search(r'(?<![a-z0-9])' + re.escape(f) + r'(?![a-z0-9])', qe):
                s = 0.9 + min(len(n), 30) / 300                      # longest contained name wins
                if f in qe: s += 0.05
            else:
                s = max(difflib.SequenceMatcher(None, qe, n).ratio(), difflib.SequenceMatcher(None, qe, f).ratio())
                if len(qe) < 5 or len(qe.split()) > 4 and s < 0.9: s = 0
            if s > bs: best, bs = i, s
        if bs >= 0.9:                                   # contained name must make up most of the query
            cov = len(self.pname[best]) + (len(norm_en(self.p.at[best, 'Brand'])) if norm_en(self.p.at[best, 'Brand']) in qe else 0)
            if cov / max(len(qe), 1) < 0.6: return None  # 'sitting by the fireplace at night' is NOT the perfume 'By the Fireplace'
        return (best, bs) if bs >= 0.84 else None

    def similar_perfumes(self, i, k=5, fa=False):
        """vibes of perfume i = its own tags; similar perfumes = nearest on the 10 active axes
        (+ small bonus for shared vibe tags), one per family, never the same family."""
        act = np.array([a not in INACTIVE for a in AX])
        v0 = self.V[i]; W = np.where(act, 1 + np.abs(v0 - 2.5) / 1.25, 0.0)         # extreme axes count more
        d = np.abs(v0 - self.V); sim = 1 - (W * d).sum(1) / (5 * W.sum())
        shared = np.array([len(self.tags[i] & t) for t in self.tags])
        sc = sim + 0.04 * np.minimum(shared, 3)
        res, used = [], {self.fams[i]}
        for j in np.argsort(-sc):
            if not self._mask[j] or self.fams[j] in used: continue
            res.append({'perfume': self.lab[j], 'similarity': round(float(sim[j]), 2), 'shared_vibes': int(shared[j]),
                        'why': (f"{int(shared[j])} وایب مشترک" if fa else f"{int(shared[j])} shared vibes") if shared[j] else '',
                        'notes': self.p.at[j, 'Notes'], **self.card(j)}); used.add(self.fams[j])
            if len(res) == k: break
        vib = [self.v.at[self.vid.index(t), 'Vibe Title'] for t in sorted(self.tags[i], key=int) if t in self.vid]
        return vib, res

    # ---- main entry
    def recommend(self, text, gender='any', mode='auto', lang='en'):
        """gender: list of any of 'women','men','unisex' (independent categories) | 'any' (all three).
        Legacy strings: 'women' = women + unisex, 'men' = men + unisex."""
        g = self.p.Gender.astype(str).str.lower().values
        if gender == 'any': cats = {'women', 'men', 'unisex'}
        elif gender == 'women': cats = {'women', 'unisex'}
        elif gender == 'men': cats = {'men', 'unisex'}
        else: cats = {c for c in gender if c in ('women', 'men', 'unisex')} or {'women', 'men', 'unisex'}
        self._mask = np.ones(len(g), bool) if len(cats) == 3 else np.isin(g, list(cats))
        gender = 'any' if len(cats) == 3 else '+'.join(sorted(cats))
        self._lang_fa = (lang == 'fa')
        orig = text
        pf0 = self.find_perfume(text) if mode != 'vibe' else None
        if not pf0:                                           # typos in a perfume name or in a vibe sentence
            t1, ch = self.fix_typos(text, self.name_vocab, 0.78) if (mode == 'perfume' or len(text.split()) <= 4) else (text, False)
            if ch and self.find_perfume(t1): text = t1
            else:
                t2, ch2 = self.fix_typos(text)
                if ch2 and (mode == 'perfume' or float(self._sims(t2).max()) >= float(self._sims(text).max()) - 0.02): text = t2
        r = self._recommend(text, mode)
        if text != orig: r['corrected_query'] = text
        r['gender_filter'] = gender
        if r['case'] not in ('perfume', 'perfume_missing'):                # how the text was matched (for debugging / transparency)
            sims = self._sims(text); top = np.argsort(-sims)[:3]
            r['debug'] = {'backend': self.backend, 'case2_threshold': self.thr['case2'],
                          'top_vibes': [(self.vtitle[int(self.v.ID[j])], round(float(sims[j]), 3)) for j in top]}
        return r

    def fix_typos(self, text, vocab=None, cutoff=0.80):
        """Correct misspelled words against the library vocabulary (only words >= 4 letters that the library does not know)."""
        if is_fa(text): return text, False
        vocab = vocab or self.vocab; out, changed = [], False
        for w in text.split():
            core = re.sub(r"[^A-Za-z]", '', w).lower()
            if len(core) >= 4 and core not in vocab and core not in COMMON:
                m = difflib.get_close_matches(core, vocab, n=1, cutoff=cutoff)
                if m: out.append(m[0]); changed = True; continue
            out.append(w)
        return ' '.join(out), changed

    def _missing_perfume(self, text):
        """The user typed a perfume that is not in the library: suggest close names and same-brand perfumes."""
        qe = norm_en(fa_perfume_to_en(text) if is_fa(text) else text)
        sc = [max(difflib.SequenceMatcher(None, qe, n).ratio(), difflib.SequenceMatcher(None, qe, f).ratio()) for n, f in zip(self.pname, self.pfull)]
        close = [(self.lab[i], round(float(sc[i]), 2)) for i in np.argsort(sc)[::-1][:3] if sc[i] >= 0.5 and self._mask[i]]
        brands = {norm_en(b): b for b in self.p.Brand.unique()}
        bq = [b for nb, b in brands.items() if re.search(r'(?<![a-z0-9])' + re.escape(nb) + r'(?![a-z0-9])', qe)]
        same = [self.lab[i] for i in range(len(self.p)) if self.p.at[i, 'Brand'] in bq and self._mask[i]][:5]
        return {'case': 'perfume_missing', 'query': text, 'did_you_mean': close, 'brand': bq[0] if bq else None, 'same_brand': same}

    def _recommend(self, text, mode='auto'):
        fa = is_fa(text) or getattr(self, '_lang_fa', False)
        pf = self.find_perfume(text) if mode != 'vibe' else None
        if mode == 'perfume' and not pf: return self._missing_perfume(text)
        if mode == 'auto' and not pf and len(text.split()) <= 6:
            m = self._missing_perfume(text)
            if m['brand']: return m                     # a known brand name in a short query = a perfume we do not have
        if pf and (len(text.split()) <= 6):
            i, s = pf
            vib, sim = self.similar_perfumes(i, fa=fa)
            return {'case': 'perfume', 'matched_perfume': self.lab[i], 'confidence': round(s, 2),
                    'its_vibes': vib, 'its_vibe_stories': [(self.vtitle[int(t)], self.vstory[int(t)]) for t in sorted(self.tags[i], key=int) if t.isdigit() and int(t) in self.vtitle],
                    'perfume_card': self.card(i), 'similar_perfumes': sim}
        # case 1: exact title / keyword (English text, or Persian after glossary translation)
        te = norm_en(fa_to_en(text) if fa and self.backend == 'tfidf' else text)
        for j in range(len(self.v)):
            if te and (te == self.title_n[j] or te in self.kw[j] and len(te.split()) <= 2):
                return self._vibe_result(1, [j], [1.0], text, fa)
        sims = self._sims(text); order = np.argsort(-sims); j0 = int(order[0])
        ok2 = sims[j0] >= self.thr['case2']
        if self.backend == 'tfidf':                      # char n-grams alone gave false matches ('hospital' -> 'cardamom')
            wj = self._last_word[j0]
            ok2 = (sims[j0] >= self.thr['case2'] and wj > 0.08) or (sims[j0] >= 0.15 and wj >= 0.25)
        if ok2:                                                                          # case 2
            return self._vibe_result(2, [j0], [float(sims[j0])], text, fa)
        # case 3: estimate the 12 numbers from the nearest vibes (similarity-weighted average)
        top = [int(j) for j in order[:5]]; w = np.maximum(sims[top], 1e-6) ** 2; w = w / w.sum()
        T = (self.T[top] * w[:, None]).sum(0); Wt = (self.W[top] * w[:, None]).sum(0)
        rows = self.rank_target(T, Wt, bonus={self.vid[j]: float(wi) for j, wi in zip(top[:3], w[:3])})
        weak = sims[j0] < self.thr['case3_floor']
        return {'case': 3, 'weak': bool(weak), 'note': ('no close vibe in the library - the answer is a rough estimate' if not fa else
                                    'وایب نزدیکی در کتابخانه نبود؛ پیشنهاد تقریبی است') if weak else
                ('closest vibes were blended' if not fa else 'ترکیب نزدیک‌ترین وایب‌ها'),
                'nearest_vibes': [(self.v.at[j, 'Vibe Title'], round(float(sims[j]), 2)) for j in top[:3]],
                'nearest_vibe_stories': [(self.v.at[j, 'Vibe Title'], self.vstory[int(self.v.at[j, 'ID'])]) for j in top[:3]],
                'estimated_targets': {a: round(float(T[k]), 1) for k, a in enumerate(AX) if a not in INACTIVE},
                'perfumes': self._perf(rows, T, Wt, fa)}

    def _vibe_result(self, case, js, sims, text, fa):
        j = js[0]; rows = []
        if self._mask.all():                      # no gender filter -> the precomputed matches of the workbook
            for k in (1, 2, 3):
                lbl = self.v.at[j, f'Match {k}']
                if lbl in self.lab: rows.append((self.lab.index(lbl), float(self.v.at[j, f'Match {k} Score'])))
        else:                                     # gender filter -> same ranking formula, restricted to allowed perfumes
            rows = self.rank_target(self.T[j], self.W[j], bonus={self.vid[j]: 1.5})
        return {'case': case, 'vibe': f"{int(self.v.at[j, 'ID'])} {self.v.at[j, 'Vibe Title']}", 'similarity': round(sims[0], 2), 'vibe_story': self.vstory[int(self.v.at[j, 'ID'])],
                'perfumes': self._perf(rows, self.T[j], self.W[j], fa)}


def show(r):
    print(f"case: {r['case']}")
    for k in ('vibe', 'note', 'matched_perfume', 'confidence', 'its_vibes', 'nearest_vibes', 'estimated_targets'):
        if k in r: print(f"  {k}: {r[k]}")
    for x in r.get('perfumes', []) + r.get('similar_perfumes', []):
        print('  -', x['perfume'], x['similarity'], '|', x.get('why', ''), '| notes:', str(x['notes'])[:70])

if __name__ == '__main__':
    e = Engine(sys.argv[2] if len(sys.argv) > 2 else 'VIBE_final_v25.xlsx')
    print('[backend]', e.backend)
    show(e.recommend(sys.argv[1] if len(sys.argv) > 1 else 'sunset by the sea'))
