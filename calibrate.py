"""Calibration for the AI engine. Run inside the vibe environment:
    conda activate vibe
    python calibrate.py
It writes calibrate_out.txt (send that file back)."""
import csv, io
import numpy as np
from vibe_engine import Engine

XLSX = 'VIBE_final_v25.xlsx'
TEST = [
    ('library', 'a quiet sunset by the sea'), ('library', 'walking through an autumn forest'), ('library', 'a date at a jazz bar'),
    ('library', 'a rainy afternoon in a quiet cafe'), ('library', 'a spring morning at a flower market'),
    ('reworded', 'the sun going down over the ocean, salt on my skin'), ('reworded', 'cold leaves under my boots in October'),
    ('reworded', 'whisky, low lights and a saxophone'), ('reworded', 'coffee and rain on the window'), ('reworded', 'fresh tulips and wet petals'),
    ('unrelated', 'a hospital waiting room'), ('unrelated', 'my first day at a new office'), ('unrelated', 'doing my taxes'),
    ('unrelated', 'a traffic jam on the highway'), ('unrelated', 'a dentist appointment'), ('unrelated', 'cleaning the bathroom'),
    ('unrelated', 'a spreadsheet meeting'), ('unrelated', 'waiting for the bus in the rain'),
    ('persian', 'غروب کنار دریا'), ('persian', 'بوی بارون روی خاک'), ('persian', 'یک کافه دنج در زمستان'),
    ('persian', 'صبحانه در هتل'), ('persian', 'جنگل و بوی چوب سوخته'),
]
REAL = [
"sunset by the sea",
"After sex",
"cool",
"از منزل بیرون میام هوا رو به خنکی قبلش باران اومده و بوی تازگی درختان و زمین",
"بوی قهوه و سیگار قاطی یعنی قهوه خوردی بعدش سیگار میکشی در هوای نمناک خوب",
"Aventus",
"black opium",
"rain on soil",
"rain",
"libre",
"Floral",
"Mindful And calm",
"جنگل و عطر چوبی که میسوزه",
"A nice wind by the ocean with drizzles falling",
"Summer time breeze",
"Blue de Chanel",
"exotic",
"danxe",
"dance",
"First of spring",
"Writing A quiet luxury evening in a modern Parisian hotel. Warm amber light, polished wood, soft leather, a perfectly tailored black suit, and the subtle confidence of someone who doesn't need to impress anyone. Sophisticated, sensual, elegant, woody, and slightly mysterious. Looking for a refined niche fragrance with beautiful projection and lasting power, not overly sweet or loud.",
"Writing A carefree summer afternoon on the Mediterranean coast. Salty sea breeze, sun-warmed skin, white linen, sparkling citrus, and the feeling of diving into crystal-clear turquoise water. Fresh, airy, luminous, natural, and effortlessly joyful. I want a fragrance that feels like sunshine on my skin, not a heavy or overly sweet perfume.",
"Driving a chic and luxury car near the beach",
"Driving a luxury car near the beach",
"یک شب رمانتیک در یک رستوران مجلل",
"دورهمی صبحانه زنانه در هتل استقلال",
"پرسه در جنگلهای شمال",
"بارون باریده هوا و زمین و درختا بوی تازگی میده با اولین نفسی که میکشی انگار زنده میشی",
"chanel mademoiselles",
"Top notes of bergamot, pink pepper, and pear blossom; middle notes of lily of the valley, peony, and heliotrope; and base notes of orris root, sandalwood, and milky musk. (Revlon)",
"the first of new year",
"A Winter Night under The northern lights",
"First night at the Metropolitan Opera, a lot of people,  all of them wearing their best,",
"Coming home from the funeral of the dear person.",
"Gothic library with fire and snow is falling",
"Cozy winter evening",
"Opening night at the Opera",
"car fire",
"cafe at night",
"Shower after sport",
"a rose flavoured turkish delight",
"Carefree, on the way in the train to a new city to explore. Morning, sun shines and cool breeze",
"a quiet sunset by the sea",
"breakfast in hotel",
"A rainy afternoon in a quiet cafe with a good book",
"A Rainy Afternoon in a Quiet Café",
"A Spring Morning at a Flower Market",
"A Sad Sunset",
"Brazilian Samba Dance",
"Strolling in Neauphle-le-Château",
"listen to love music"
]

old = Engine(XLSX, backend='tfidf')
ai = Engine(XLSX, backend='fe')
out = io.StringIO(); w = csv.writer(out, delimiter='\t')
w.writerow(['group', 'phrase', 'old_case', 'ai_case', 'ai_corrected', 'sim1', 'vibe1', 'sim2', 'vibe2', 'sim3', 'vibe3', 'ai_perfumes'])
for g, q in TEST + [('real', q) for q in REAL]:
    try:
        a, b = old.recommend(q), ai.recommend(q)
        s = ai._sims(q); top = np.argsort(-s)[:3]
        names = [x.get('perfume', '') for x in (b.get('perfumes') or b.get('similar_perfumes') or [])][:3]
        row = [g, q, a['case'], b['case'], b.get('corrected_query', '')]
        for j in top: row += [f'{s[j]:.3f}', ai.vtitle[int(ai.v.ID[j])]]
        w.writerow(row + [' | '.join(names)])
    except Exception as e:
        w.writerow([g, q, 'ERROR', type(e).__name__, str(e)[:80]])
open('calibrate_out.txt', 'w', encoding='utf-8').write('AI backend: ' + ai.backend + '\n' + out.getvalue())
print('Done. Send calibrate_out.txt')
