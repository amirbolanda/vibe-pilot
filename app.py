"""One-page MVP.  Run:  pip install streamlit sentence-transformers pandas scikit-learn openpyxl
                       streamlit run app.py        (VIBE_final_v25.xlsx and vibe_engine.py in the same folder)"""
import html
import streamlit as st
from vibe_engine import Engine
import os
import persist
import feedback_store as fb

st.set_page_config(page_title="Vibe → Perfume", page_icon="🌫️", layout="centered")
import streamlit.components.v1 as components
components.html('''<script>
(function(){var d=window.parent.document;
 d.querySelectorAll('meta[name="google"]').forEach(function(m){m.remove();});       // allow Google Translate
 d.documentElement.setAttribute('lang','en'); d.documentElement.setAttribute('translate','yes'); d.documentElement.classList.remove('notranslate');
 var P=window.parent.Node.prototype;                                                  // keep the page alive when the translator wraps text in <font>
 if(!P.__patched){P.__patched=true;var rc=P.removeChild;P.removeChild=function(c){if(c.parentNode!==this){return c;}return rc.apply(this,arguments);};
  var ib=P.insertBefore;P.insertBefore=function(n,r){if(r&&r.parentNode!==this){return n;}return ib.apply(this,arguments);};}})();
</script>''', height=0)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&display=swap');
.hero{text-align:center;padding:1.6rem 0 .6rem}
.hero h1{font-family:'Cormorant Garamond',Georgia,serif;font-weight:600;font-size:2.7rem;line-height:1.1;margin:0;letter-spacing:.01em}
.hero p{font-family:'Cormorant Garamond',Georgia,serif;font-style:italic;font-size:1.25rem;opacity:.7;margin:.4rem 0 0}
.card h3,.vibe h4{font-family:'Cormorant Garamond',Georgia,serif;font-size:1.55rem}
.story,.vibe p{font-family:'Cormorant Garamond',Georgia,serif;font-size:1.12rem}
.moods{display:grid;grid-template-columns:repeat(5,1fr);gap:.6rem;margin:.6rem 0 .3rem}
.moods div{font-size:.66rem;letter-spacing:.08em;text-transform:uppercase;opacity:.75}
.moods i{display:block;height:4px;border-radius:2px;margin-top:.25rem;background:rgba(128,128,128,.2);overflow:hidden}.moods i b{display:block;height:4px;border-radius:2px}
.row{display:flex;gap:1rem;align-items:flex-start;justify-content:space-between}.row .main{flex:1;min-width:0}.bottle{flex:0 0 auto;filter:drop-shadow(0 8px 14px rgba(0,0,0,.25))}
.story{position:relative;padding:.2rem 0 .2rem 1.6rem;font-size:1.25rem!important;line-height:1.5}.story:before{content:'\201C';position:absolute;left:0;top:-.5rem;font-size:3rem;opacity:.35;font-family:Georgia,serif}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
.card,.vibe{animation:rise .55s ease both}.card:nth-of-type(2){animation-delay:.08s}
.card{transition:transform .15s} .card:hover{transform:translateY(-2px)}
@media(max-width:600px){.hero h1{font-size:2rem}.moods{grid-template-columns:repeat(3,1fr)}}
</style>""", unsafe_allow_html=True)
st.markdown("""
<style>
.block-container{max-width:760px}
.vibe{border-left:3px solid #b08d57;padding:.4rem 1rem;margin:.6rem 0 1.2rem;background:rgba(176,141,87,.07);border-radius:0 8px 8px 0}
.vibe h4{margin:0 0 .25rem;font-weight:600} .vibe p{margin:0;font-style:italic;opacity:.85}
.card{border:1px solid rgba(128,128,128,.25);border-radius:14px;padding:1.1rem 1.25rem;margin:0 0 1rem}
.card .brand{font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;opacity:.6}
.card h3{margin:.1rem 0 .35rem;font-weight:600}
.meta span{display:inline-block;font-size:.74rem;padding:.12rem .55rem;margin:0 .3rem .3rem 0;border-radius:999px;border:1px solid rgba(128,128,128,.35)}
.story{font-style:italic;opacity:.85;margin:.5rem 0 .7rem}
.lbl{font-size:.68rem;letter-spacing:.12em;text-transform:uppercase;opacity:.55;margin:.5rem 0 .2rem}
.chip{display:inline-block;font-size:.8rem;padding:.1rem .55rem;margin:0 .3rem .3rem 0;border-radius:6px;background:rgba(128,128,128,.14)}
.chip.a{background:rgba(176,141,87,.18)}
.bar{height:5px;border-radius:3px;background:rgba(128,128,128,.2);margin:.1rem 0 .5rem}.bar i{display:block;height:5px;border-radius:3px;background:#b08d57}
.why{font-size:.78rem;opacity:.6}
</style>""", unsafe_allow_html=True)

@st.cache_resource
def load():
    if not os.path.exists('VIBE_final_v25.xlsx'): persist.fetch('VIBE_final_v25.xlsx')      # deployed: the workbook lives in a private repo
    return Engine('VIBE_final_v25.xlsx')
e = load()
if 'user' not in st.session_state: st.session_state.user = fb.new_user()
E = lambda x: html.escape(str(x))
lang_sel = st.radio("Language / زبان", ["English", "فارسی"], horizontal=True, key='lang_sel')
FA = lang_sel == "فارسی"
L = lambda en, fa: fa if FA else en                                     # pick the UI string
tx = lambda s: e.tr.get(str(s).strip(), s) if FA else s                  # library text (stories, vibe titles) in the chosen language
GEN_FA = {'women': 'زنانه', 'men': 'مردانه', 'unisex': 'یونیسکس'}
SEG_FA = {'niche': 'نیچ', 'designer': 'برند طراح', 'middle-eastern': 'خاورمیانه‌ای'}
ACC_FA = {'Aldehydic': 'آلدهیدی', 'Almond': 'بادام', 'Amber': 'عنبر', 'Animalic': 'حیوانی', 'Aquatic': 'آبی', 'Aromatic': 'معطر', 'Balsamic': 'بالسامی', 'Berry': 'توت',
 'Boozy': 'الکلی', 'Bright': 'درخشان', 'Cacao': 'کاکائو', 'Caramel': 'کارامل', 'Cherry': 'آلبالو', 'Chocolate': 'شکلات', 'Cinnamon': 'دارچین', 'Citrus': 'مرکبات',
 'Clean': 'پاکیزه', 'Coconut': 'نارگیل', 'Coffee': 'قهوه', 'Creamy': 'خامه‌ای', 'Dark': 'تیره', 'Dark Floral': 'گلی تیره', 'Dry': 'خشک', 'Earthy': 'خاکی',
 'Elegant': 'باوقار', 'Floral': 'گلی', 'Fougere': 'فوژر', 'Fresh': 'تازه', 'Fresh Spicy': 'ادویه‌ای تازه', 'Fruity': 'میوه‌ای', 'Gourmand': 'خوراکی‌شیرین',
 'Green': 'سبز', 'Herbal': 'گیاهی', 'Honey': 'عسل', 'Honeyed': 'عسلی', 'Incense': 'بخور', 'Iris': 'زنبق', 'Lavender': 'اسطوخودوس', 'Leather': 'چرم',
 'Leathery': 'چرمی', 'Marine': 'دریایی', 'Marshmallow': 'مارشمالو', 'Metallic': 'فلزی', 'Milky': 'شیری', 'Mineral': 'معدنی', 'Mossy': 'خزه‌ای', 'Musky': 'مشکی',
 'Narcotic': 'مست‌کننده', 'Nutty': 'مغزی', 'Oud': 'عود', 'Patchouli': 'پچولی', 'Peach': 'هلو', 'Powdery': 'پودری', 'Resinous': 'صمغی', 'Rose': 'رز',
 'Saffron': 'زعفران', 'Salty': 'شور', 'Sandalwood': 'چندن', 'Sensual': 'حسی', 'Skin Scent': 'بوی پوست', 'Smoky': 'دودی', 'Soft': 'ملایم', 'Soft Floral': 'گلی ملایم',
 'Soft Spicy': 'ادویه‌ای ملایم', 'Soft Sweet': 'شیرین ملایم', 'Solar': 'آفتابی', 'Sour': 'ترش', 'Spicy': 'ادویه‌ای', 'Suede': 'جیر', 'Sweet': 'شیرین',
 'Sweet Fresh': 'شیرین و تازه', 'Synthetic': 'مصنوعی', 'Tobacco': 'تنباکو', 'Tropical': 'استوایی', 'Tuberose': 'مریم', 'Vanilla': 'وانیل', 'Violet': 'بنفشه',
 'Warm': 'گرم', 'Warm Spicy': 'ادویه‌ای گرم', 'White Floral': 'گل سفید', 'Woody': 'چوبی', 'Yellow Floral': 'گل زرد'}
if FA: st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@200;300;400;500&display=swap');
.stMarkdown,.stCaption,p,li,label,h1,h2,h3,h4,input,textarea,button,.chip,.hero h1,.hero p,.card h3,.vibe h4,.story,.vibe p,.moods div,.lbl,.why,.meta span{font-family:'Vazirmatn','Vazir',Tahoma,sans-serif!important}
.stMarkdown,.stCaption,p,li,label,input,textarea,button{font-weight:300!important;line-height:1.95!important}
.hero h1{font-weight:400!important;font-size:2.1rem!important;line-height:1.5!important;letter-spacing:0!important}
.hero p{font-weight:200!important;font-style:normal!important;font-size:1.05rem!important;opacity:.75}
h2,h3,h4,.card h3,.vibe h4{font-weight:400!important;font-size:1.25rem!important;line-height:1.6!important}
.story,.vibe p{font-style:normal!important;font-weight:300!important;font-size:1rem!important;line-height:2.1!important;opacity:.92}
.story{padding:.2rem 1.6rem .2rem 0!important}.story:before{left:auto!important;right:0!important}
.chip,.meta span,.moods div,.lbl,.why{font-weight:300!important;letter-spacing:0!important;text-transform:none!important}
.chip{font-size:.78rem!important}.card .brand{font-family:Georgia,serif!important}
</style>""", unsafe_allow_html=True)
if FA: st.markdown('<style>.block-container{direction:rtl;text-align:right}.chip{unicode-bidi:plaintext}.card h3,.brand{direction:ltr;text-align:left}[data-testid=stRadio] label,[data-testid=stCheckbox] label{direction:rtl}.vibe{border-left:0!important;border-right:3px solid #b08d57;border-radius:8px 0 0 8px!important}</style>', unsafe_allow_html=True)
def chips(csv, cls=''):
    return ''.join(f'<span class="chip {cls}">{E(t.strip())}</span>' for t in str(csv).split(',') if t.strip())

PALS = {'fresh': ('#2b7a9b', '#7fd1c7'), 'warm': ('#c2703a', '#f0c27b'), 'dark': ('#4a3470', '#9a6b94'), 'floral': ('#b4577a', '#f2b5c8')}
PAL = ('#b08d57', '#e3cfa3')
def palette(ax):
    """mood colours of a perfume from its axes: fresh / warm-sweet / dark-smoky / floral-fruity"""
    if not ax: return PAL
    sc = {'fresh': ax['Freshness'], 'warm': (ax['Thermal'] + ax['Sweetness']) / 2,
          'dark': (ax['Smoky-Spicy'] + ax['Woody-Earthy'] + ax['Intensity']) / 3, 'floral': (ax['Floral'] + ax['Fruity']) / 2}
    return PALS[max(sc, key=sc.get)]
def rgba(h, al): return f"rgba({int(h[1:3],16)},{int(h[3:5],16)},{int(h[5:7],16)},{al})"
ACC = [('citrus', '#e0b341'), ('aquatic', '#3a9bb5'), ('marine', '#3a9bb5'), ('fresh', '#4aa37a'), ('green', '#4aa37a'), ('floral', '#d9739a'), ('rose', '#d9739a'),
       ('iris', '#a58bc7'), ('woody', '#9a7448'), ('oud', '#7a5a4a'), ('smoky', '#7a6a8a'), ('leather', '#8a5a3a'), ('tobacco', '#8a6a3a'), ('spicy', '#c45c3b'),
       ('vanilla', '#d9a85c'), ('sweet', '#c98a52'), ('gourmand', '#c98a52'), ('fruity', '#d96a5b'), ('amber', '#c08a2e'), ('resinous', '#c08a2e'),
       ('musk', '#a89cb0'), ('powdery', '#b9a9c9'), ('coffee', '#7a5a42'), ('boozy', '#a0522d'), ('earthy', '#7d6b4a')]
def acc_color(t):
    t = t.lower()
    for k, c in ACC:
        if k in t: return c
    return '#888888'
def accord_chips(csv):
    return ''.join(f'<span class="chip" style="background:{rgba(acc_color(t), .2)};border-left:3px solid {acc_color(t)}">{E(ACC_FA.get(t.strip(), t.strip()) if FA else t.strip())}</span>' for t in str(csv).split(',') if t.strip())
def mood_bars(ax, col):
    if not ax: return ''
    items = [(L('Fresh', 'تازگی'), ax['Freshness']), (L('Sweet', 'شیرینی'), ax['Sweetness']), (L('Warm', 'گرمی'), ax['Thermal']), (L('Intense', 'شدت'), ax['Intensity']), (L('Smoky', 'دودی'), ax['Smoky-Spicy'])]
    return '<div class="moods">' + ''.join(f'<div>{n}<i><b style="width:{min(max(v, 0), 5) * 20}%;background:{col}"></b></i></div>' for n, v in items) + '</div>'

def vibe_block(title, story):
    st.markdown(f'<div class="vibe" style="border-left-color:{PAL[0]};background:linear-gradient(100deg,{rgba(PAL[0], .22)},{rgba(PAL[1], .06)})"><h4>{E(tx(title))}</h4><p>“{E(tx(story))}”</p></div>', unsafe_allow_html=True)

_used = set()
def pick_story(x):
    """first of this perfume's own stories that no other card on the page already shows"""
    for t, s in x.get('stories') or []:
        if s not in _used: _used.add(s); return t, s
    return '', x['story']

def bottle(c1, c2, uid):
    """a generic (brand-free) glass bottle whose liquid carries the mood colours of the perfume"""
    return (f'<svg viewBox="0 0 90 150" width="84" height="140" xmlns="http://www.w3.org/2000/svg"><defs>'
            f'<linearGradient id="l{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c2}"/><stop offset="1" stop-color="{c1}"/></linearGradient>'
            f'<linearGradient id="g{uid}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity=".45"/><stop offset=".35" stop-color="#fff" stop-opacity=".05"/><stop offset="1" stop-color="#fff" stop-opacity=".18"/></linearGradient>'
            f'<radialGradient id="h{uid}"><stop offset="0" stop-color="{c1}" stop-opacity=".55"/><stop offset="1" stop-color="{c1}" stop-opacity="0"/></radialGradient></defs>'
            f'<ellipse cx="45" cy="132" rx="42" ry="14" fill="url(#h{uid})"/>'
            f'<rect x="33" y="6" width="24" height="20" rx="4" fill="{c1}" opacity=".9"/><rect x="38" y="24" width="14" height="10" fill="#cfd3d8" opacity=".7"/>'
            f'<rect x="12" y="34" width="66" height="96" rx="14" fill="url(#l{uid})" opacity=".92"/>'
            f'<rect x="12" y="34" width="66" height="96" rx="14" fill="url(#g{uid})"/>'
            f'<rect x="12" y="34" width="66" height="96" rx="14" fill="none" stroke="#ffffff" stroke-opacity=".5" stroke-width="1.5"/>'
            f'<rect x="26" y="62" width="38" height="34" rx="3" fill="#ffffff" opacity=".16"/></svg>')

def perfume_card(i, x):
    st_title, st_text = pick_story(x)
    meta = [x['concentration'], GEN_FA.get(x['gender'], x['gender']) if FA else x['gender'].title(), SEG_FA.get(x['segment'], x['segment']) if FA else str(x['segment']).title()] + ([str(x['year'])] if x.get('year') else [])
    pct = int(x['similarity'] * 100)
    c1, c2 = palette(x.get('axes'))
    st.markdown(f"""<div class="card" style="border-left:4px solid {c1};background:linear-gradient(135deg,{rgba(c1, .16)},transparent 60%)">
<div class="row"><div class="main">
<div class="brand">{E(x['brand'])}</div><h3>{i}. {E(x['name'])}</h3>
<div class="meta">{''.join(f'<span>{E(m)}</span>' for m in meta if m)}</div>
<div class="why">{L('match', 'تطابق')} {pct}%{(' · ' + E(x['why'])) if x.get('why') else ''}</div><div class="bar"><i style="width:{pct}%;background:linear-gradient(90deg,{c1},{c2})"></i></div>
</div><div class="bottle">{bottle(c1, c2, i)}</div></div>
<div class="story">“{E(tx(st_text))}”{('<br><span class="why">— ' + E(tx(st_title)) + '</span>') if st_title else ''}</div>
{mood_bars(x.get('axes'), c1)}
<div class="lbl">{L('Notes', 'نت‌ها')}</div><div dir="ltr" style="text-align:left">{chips(x['notes'])}</div>
<div class="lbl">{L('Accords', 'اکوردها')}</div>{accord_chips(x['accords'])}
</div>""", unsafe_allow_html=True)
    if st.button(L("♡ I'd like to try this", "♡ می‌خواهم امتحانش کنم"), key=f"try_{st.session_state.get('sid')}_{i}"):
        fb.log_interest(st.session_state.get('sid'), st.session_state.user, x['perfume'])
        st.success(L("Noted! We'll tell you when sample boxes are ready.", "ثبت شد! وقتی جعبه‌ی نمونه آماده شد خبرتان می‌کنیم."))

st.markdown(f'<div class="hero"><h1>{L("Which perfume matches your vibe?", "کدام عطر به حال‌وهوای تو می‌خورد؟")}</h1><p>{L("Describe a feeling. Find your scent.", "یک حس را توصیف کن، عطرش را پیدا کن.")}</p></div>', unsafe_allow_html=True)
st.caption(L("Pilot version: we log your searches anonymously to improve the results. No personal data is stored unless you choose to share it at the end.",
             "نسخه‌ی آزمایشی: جستجوهای شما بدون نام ثبت می‌شود تا نتایج بهتر شود. هیچ اطلاعات شخصی ذخیره نمی‌شود، مگر خودتان در پایان بخواهید."))
st.caption(L("Describe a mood, a place, a moment - or type a perfume you already like.", "یک حال‌وهوا، یک مکان یا یک لحظه را توصیف کنید، یا اسم عطری را که دوست دارید بنویسید."))
# Widget labels are kept constant (the visible text is drawn separately), so switching the language never resets what the user typed or chose.
st.markdown(L("**I'm looking for** (choose any)", "**دنبال چه عطری هستم** (هر تعداد که خواستید انتخاب کنید)"))
GN = {"women": L("Women's", "زنانه"), "men": L("Men's", "مردانه"), "unisex": L("Unisex", "یونیسکس")}
if 'gsel' not in st.session_state: st.session_state['gsel'] = {k: True for k in GN}      # remembered choice, survives a language switch
gc = st.columns(3); gender = []
for k, col in zip(GN, gc):
    on = col.checkbox(GN[k], value=st.session_state['gsel'][k], key=f"g_{k}_{int(FA)}")
    st.session_state['gsel'][k] = on
    if on: gender.append(k)
if not gender: st.caption(L("Nothing selected - showing all perfumes.", "چیزی انتخاب نشده؛ همه‌ی عطرها نشان داده می‌شود.")); gender = "any"
st.markdown(L("**Search by**", "**جستجو بر اساس**"))
MODES = {0: L("Vibe or perfume (auto)", "حال‌وهوا یا عطر (خودکار)"), 1: L("A perfume name", "اسم یک عطر")}
mode = "auto" if st.radio("mode", [0, 1], format_func=MODES.get, horizontal=True, key="mode_sel", label_visibility="collapsed") == 0 else "perfume"
if mode == "perfume":
    st.markdown(L("**Your perfume**", "**عطر شما**")); st.caption(L("e.g. Aventus · Bleu de Chanel · Libre", "مثلاً Aventus · Bleu de Chanel · Libre یا ساواژ دیور"))
else:
    st.markdown(L("**Your vibe**", "**حال‌وهوای شما**")); st.caption(L("e.g. sunset by the sea · a cafe in Florence · Aventus", "مثلاً غروب کنار دریا · یک کافه در فلورانس · Aventus"))
q = st.text_input("query", key="q_" + mode, label_visibility="collapsed")
if q.strip():
    r = e.recommend(q.strip(), gender=gender, mode=mode, lang='fa' if FA else 'en')
    if r.get('corrected_query'): st.caption(L(f"Showing results for “{r['corrected_query']}”", f"نتایج برای «{r['corrected_query']}»"))
    if r['case'] == 'perfume_missing':
        if st.session_state.get('miss_q') != q: fb.log_missing(st.session_state.user, q.strip(), r['brand']); st.session_state.miss_q = q
        st.subheader(L("We don't have this perfume yet", "این عطر هنوز در کتابخانه‌ی ما نیست"))
        st.write(L("We've noted it, so we can add it. In the meantime:", "یادداشتش کردیم تا اضافه‌اش کنیم. تا آن موقع:"))
        if r['did_you_mean']: st.write(L('**Did you mean:** ', '**شاید منظورتان این بود:** ') + ' · '.join(n for n, _ in r['did_you_mean']))
        if r['same_brand']: st.write(L(f"**Other {r['brand']} perfumes we have:** ", f"**عطرهای دیگر {r['brand']} که داریم:** ") + ' · '.join(r['same_brand']))
        st.markdown(L("Describe how it smells or the mood you want from it (a few words)", "بوی آن یا حال‌وهوایی که از آن می‌خواهید را چند کلمه توصیف کنید"))
        desc = st.text_input("desc", key='desc_' + q, label_visibility="collapsed")
        if desc.strip():
            q, r = desc.strip(), e.recommend(desc.strip(), gender=gender, mode='vibe', lang='fa' if FA else 'en')
        else: st.stop()
    _src = r.get('perfume_card') if r['case'] == 'perfume' else (r['perfumes'][0] if r.get('perfumes') else None)
    PAL = palette(_src.get('axes')) if _src else PAL
    st.markdown(f"<style>.stApp{{background:radial-gradient(900px 520px at 12% -6%,{rgba(PAL[0], .30)},transparent 62%),radial-gradient(800px 520px at 100% 8%,{rgba(PAL[1], .20)},transparent 58%)}}</style>", unsafe_allow_html=True)
    if r['case'] == 'perfume':
        c = r['perfume_card']
        st.subheader(L(f"You like {c['name']} by {c['brand']}", f"شما {c['name']} از {c['brand']} را دوست دارید"))
        st.caption(L("Its vibes", "وایب‌های آن"))
        for t, s in r['its_vibe_stories'][:3]: vibe_block(t, s)
        st.subheader(L("Perfumes with a similar character", "عطرهایی با شخصیت مشابه"))
        items = r['similar_perfumes'][:3]
    else:
        if r['case'] in (1, 2):
            st.subheader(L("Your vibe", "وایب شما") if r['case'] == 1 else L("Closest vibe we know", "نزدیک‌ترین وایبی که می‌شناسیم"))
            vibe_block(r['vibe'].split(' ', 1)[1], r['vibe_story'])
        else:
            st.subheader(L("We don't have this exact vibe - here are the closest ones", "این وایب دقیقاً در کتابخانه نیست؛ این‌ها نزدیک‌ترینند"))
            if r.get('weak'): st.warning(L("This one is far from everything we know; treat it as a rough guess.", "این حال‌وهوا با همه‌ی چیزهایی که می‌شناسیم فاصله دارد؛ پیشنهاد فقط یک حدس تقریبی است."))
            for t, s in r['nearest_vibe_stories']: vibe_block(t, s)
        st.subheader(L("Your three perfumes", "سه عطر شما"))
        items = r['perfumes']
    key = (q, str(gender))
    if st.session_state.get('last_q') != key:
        st.session_state.sid = fb.log_search(st.session_state.user, q.strip(), r); st.session_state.last_q = key
    _used.clear()
    for i, x in enumerate(items, 1): perfume_card(i, x)
    # ---- pilot feedback: per-perfume rating (stored anonymously)
    if r.get('debug'):
        with st.expander("How was this matched?"):
            d = r['debug']
            st.write(f"Mode: **{ {1: 'exact vibe', 2: 'similar vibe', 3: 'estimated from nearest vibes'}[r['case']] }** · backend `{d['backend']}` · similar-vibe threshold {d['case2_threshold']}")
            st.write("Closest vibes in our library: " + " · ".join(f"{t} ({s})" for t, s in d['top_vibes']))
            st.write(f"Gender filter: {r['gender_filter']}")
    st.divider()
    RATE = {"fits": L("fits", "می‌خورد"), "partly": L("partly", "تا حدی"), "no": L("no", "نمی‌خورد")}
    with st.form(f"rate_{st.session_state.sid}"):
        st.markdown(L("**Does each perfume fit the vibe you had in mind?**", "**آیا هر عطر با حال‌وهوایی که در ذهن داشتید می‌خورد؟**"))
        names = [x['perfume'] for x in items]
        picks = {n: st.radio(n, list(RATE), format_func=RATE.get, horizontal=True, key=f"{st.session_state.sid}{n}") for n in names}
        if st.form_submit_button(L("Send my rating", "ثبت نظر من")):
            fb.log_ratings(st.session_state.sid, st.session_state.user, picks); st.success(L("Thank you!", "ممنون!"))

st.divider()
with st.expander(L("Finished testing? Give us 2 minutes of feedback", "تست تمام شد؟ دو دقیقه نظرتان را بگویید")):
    YN = {"yes": L("yes", "بله"), "maybe": L("maybe", "شاید"), "no": L("no", "نه")}
    with st.form("survey"):
        score = st.slider(L("How close were the suggestions to your mood? (1 = not at all, 10 = perfectly)", "پیشنهادها چقدر به حال‌وهوای شما نزدیک بود؟ (۱ = اصلاً، ۱۰ = کاملاً)"), 1, 10, 7)
        how = st.text_input(L("How do you usually choose a perfume today?", "معمولاً چطور عطر انتخاب می‌کنید؟"))
        use = st.radio(L("Would you use a tool like this next time you buy perfume?", "دفعه‌ی بعد که عطر می‌خرید از چنین ابزاری استفاده می‌کنید؟"), list(YN), format_func=YN.get, horizontal=True)
        wtp = st.text_input(L("If we sold a box of 3 samples matching your vibe, what would you pay? (a number, in USD)", "اگر یک جعبه‌ی ۳ نمونه‌ی مناسب وایب شما می‌فروختیم، چقدر می‌پرداختید؟ (یک عدد، به دلار)"))
        miss = st.text_area(L("What was missing or wrong?", "چه چیزی کم یا اشتباه بود؟"))
        st.markdown("---")
        st.caption(L("Optional. We only store your details if you tick the box, and only use them to credit your quote. You can ask us to delete them at any time.",
                     "اختیاری. فقط اگر تیک بزنید اطلاعاتتان ذخیره می‌شود و فقط برای ذکر نام شما کنار نقل‌قول استفاده می‌شود. هر وقت بخواهید می‌توانید حذفش را بخواهید."))
        consent = st.checkbox(L("You may quote my feedback with my name, role and links", "اجازه می‌دهم نظرم با نام، نقش و لینک‌هایم نقل شود"))
        c1, c2 = st.columns(2)
        name = c1.text_input(L("Name", "نام")); role = c2.text_input(L("Role / city", "نقش / شهر"))
        email = c1.text_input(L("Email (optional)", "ایمیل (اختیاری)")); lin = c2.text_input(L("LinkedIn (optional)", "لینکدین (اختیاری)"))
        quote = st.text_area(L("A sentence we may quote (optional)", "یک جمله که می‌توانیم نقل کنیم (اختیاری)"))
        if st.form_submit_button(L("Submit feedback", "ارسال نظر")):
            fb.log_survey(st.session_state.user, dict(score=score, how_choose=how, would_use=use, wtp=wtp, missing=miss, consent=consent,
                          name=name, role=role, email=email, linkedin=lin, quote=quote)); st.success(L("Thank you - this really helps.", "ممنون؛ خیلی کمک می‌کند."))

st.markdown("---")
st.caption("© 2026 Amirmasoud Bolanda. All rights reserved. The idea, concept, vibe database and matching method of this product were created by Amirmasoud Bolanda. "
           "Any copying, reuse or commercial use without written permission is prohibited and may be subject to legal action.")
if FA: st.caption("© ۲۰۲۶ امیرمسعود بلندا. تمامی حقوق محفوظ است. ایده، مفهوم، پایگاه‌داده‌ی وایب‌ها و روش تطبیق این محصول متعلق به امیرمسعود بلندا است و هرگونه کپی، استفاده‌ی مجدد یا تجاری بدون اجازه‌ی کتبی ممنوع است و پیگرد قانونی دارد.")
