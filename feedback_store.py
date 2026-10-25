"""SQLite storage for the pilot feedback. No server needed; the file feedback.db sits next to the app."""
import sqlite3, json, time, uuid, os
import persist

DB = 'feedback.db'
if persist.ON and not os.path.exists(DB): persist.fetch(DB)          # deployed: restore the saved database after a restart
SCHEMA = """
CREATE TABLE IF NOT EXISTS searches(id TEXT PRIMARY KEY, ts REAL, user TEXT, query TEXT, case_ TEXT, vibe TEXT, perfumes TEXT, gender TEXT);
CREATE TABLE IF NOT EXISTS missing(ts REAL, user TEXT, query TEXT, brand TEXT);
CREATE TABLE IF NOT EXISTS interest(ts REAL, user TEXT, search_id TEXT, perfume TEXT);
CREATE TABLE IF NOT EXISTS ratings(search_id TEXT, user TEXT, ts REAL, perfume TEXT, rating TEXT);
CREATE TABLE IF NOT EXISTS survey(user TEXT PRIMARY KEY, ts REAL, score INTEGER, how_choose TEXT, would_use TEXT,
  wtp TEXT, missing TEXT, consent INTEGER, name TEXT, role TEXT, email TEXT, linkedin TEXT, quote TEXT);
"""
def con(path=DB):
    c = sqlite3.connect(path); c.executescript(SCHEMA)
    try: c.execute('ALTER TABLE searches ADD COLUMN gender TEXT')      # older feedback.db files
    except sqlite3.OperationalError: pass
    return c

def new_user(): return uuid.uuid4().hex[:8]          # anonymous id, not linked to a person

def log_search(user, query, res, path=DB):
    sid = uuid.uuid4().hex[:10]
    items = res.get('perfumes') or res.get('similar_perfumes') or []
    vibe = res.get('vibe') or res.get('matched_perfume') or '; '.join(t for t, _ in res.get('nearest_vibes', []))
    with con(path) as c:
        c.execute('INSERT INTO searches VALUES(?,?,?,?,?,?,?,?)', (sid, time.time(), user, query, str(res['case']), vibe,
                  json.dumps([x['perfume'] for x in items[:3]]), res.get('gender_filter', 'any')))
    persist.push_later(path)
    return sid

def log_ratings(sid, user, ratings, path=DB):        # ratings: {perfume: 'fits' | 'partly' | 'no'}
    with con(path) as c:
        c.execute('DELETE FROM ratings WHERE search_id=?', (sid,))
        c.executemany('INSERT INTO ratings VALUES(?,?,?,?,?)', [(sid, user, time.time(), p, r) for p, r in ratings.items()])
    persist.push_later(path)

def log_survey(user, d, path=DB):
    keep = d.get('consent', False)                   # contact details are stored ONLY with explicit consent
    with con(path) as c:
        c.execute('INSERT OR REPLACE INTO survey VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (user, time.time(), d.get('score'), d.get('how_choose', ''), d.get('would_use', ''), d.get('wtp', ''), d.get('missing', ''),
                   int(keep), d.get('name', '') if keep else '', d.get('role', '') if keep else '', d.get('email', '') if keep else '',
                   d.get('linkedin', '') if keep else '', d.get('quote', '') if keep else ''))
    persist.push_later(path)

def log_missing(user, query, brand, path=DB):          # perfumes people look for that we do not have = demand signal
    with con(path) as c: c.execute('INSERT INTO missing VALUES(?,?,?,?)', (time.time(), user, query, brand or ''))
    persist.push_later(path)

def log_interest(sid, user, perfume, path=DB):      # "I'd like to try this" click = purchase-intent signal
    with con(path) as c: c.execute('INSERT INTO interest VALUES(?,?,?,?)', (time.time(), user, sid, perfume))
    persist.push_later(path)
