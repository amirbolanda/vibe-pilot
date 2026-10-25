"""python report.py  ->  prints the pilot metrics and writes feedback_report.xlsx (for the pitch deck / history file)."""
import sqlite3, json, sys
import pandas as pd
path = sys.argv[1] if len(sys.argv) > 1 else 'feedback.db'
c = sqlite3.connect(path)
M = pd.read_sql('select * from missing', c) if 'missing' in [t[0] for t in c.execute("select name from sqlite_master where type='table'")] else pd.DataFrame(columns=['ts','user','query','brand']);
I = pd.read_sql('select * from interest', c) if 'interest' in [t[0] for t in c.execute("select name from sqlite_master where type='table'")] else pd.DataFrame(columns=['ts','user','search_id','perfume'])
S = pd.read_sql('select * from searches', c); R = pd.read_sql('select * from ratings', c); U = pd.read_sql('select * from survey', c)
S['when'] = pd.to_datetime(S.ts, unit='s'); R['pts'] = R.rating.map({'fits': 1, 'partly': 0.5, 'no': 0})
rated = R.groupby('search_id').agg(any_fit=('rating', lambda x: (x == 'fits').any()), n=('rating', 'size'), fit_share=('pts', 'mean')).reset_index()
m = S.merge(rated, left_on='id', right_on='search_id', how='left')
metrics = {
 'testers (anonymous ids)': S.user.nunique(), 'searches': len(S), 'searches rated': int(m.n.notna().sum()),
 'top-3 hit rate (>=1 perfume "fits")': round(float(m.any_fit.dropna().mean()), 2) if m.n.notna().any() else None,
 'perfume-level fit rate': round(float((R.rating == 'fits').mean()), 2) if len(R) else None,
 'avg overall score (1-10)': round(float(U.score.mean()), 1) if len(U) else None,
 'would use again (yes %)': round(float((U.would_use.str.lower() == 'yes').mean()), 2) if len(U) else None,
 "'I'd like to try this' clicks": len(I), 'searches with a try-click': int(I.search_id.nunique()), 'testers who clicked try': int(I.user.nunique()),
 'repeat testers (>=3 searches)': int((S.groupby('user').size() >= 3).sum()),
}
wtp = pd.to_numeric(U.wtp.str.extract(r'(\d+(?:\.\d+)?)')[0], errors='coerce')
metrics['median willingness to pay (sample box)'] = float(wtp.median()) if wtp.notna().any() else None
by_case = m.groupby('case_').agg(searches=('id', 'size'), top3_hit=('any_fit', 'mean')).round(2).reset_index()
bad = m[(m.any_fit == False) | (m.n.isna() & (m.case_ == '3'))][['when', 'query', 'case_', 'vibe']]      # missing-vibe candidates
per_perfume = R.groupby('perfume').agg(times_shown=('rating', 'size'), fits=('rating', lambda x: (x == 'fits').sum()), no=('rating', lambda x: (x == 'no').sum())).sort_values('times_shown', ascending=False).reset_index()
quotes = U[U.consent == 1][['name', 'role', 'quote', 'email', 'linkedin']]
print(pd.Series(metrics).to_string()); print(by_case.to_string(index=False))
with pd.ExcelWriter('feedback_report.xlsx') as w:
    pd.Series(metrics, name='value').to_frame().to_excel(w, sheet_name='Metrics'); by_case.to_excel(w, sheet_name='By case', index=False)
    bad.to_excel(w, sheet_name='Missing-vibe candidates', index=False); per_perfume.to_excel(w, sheet_name='Per perfume', index=False)
    S.drop(columns='ts').to_excel(w, sheet_name='All searches', index=False); U.drop(columns=['email', 'linkedin']).to_excel(w, sheet_name='Survey (no contact)', index=False)
    quotes.to_excel(w, sheet_name='Consented quotes', index=False)
    I.groupby('perfume').size().sort_values(ascending=False).rename('try clicks').reset_index().to_excel(w, sheet_name='Try-clicks per perfume', index=False)
    M.groupby('query').size().sort_values(ascending=False).rename('times searched').reset_index().to_excel(w, sheet_name='Perfumes not in library', index=False)
