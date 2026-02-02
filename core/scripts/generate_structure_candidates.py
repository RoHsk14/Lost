#!/usr/bin/env python3
import re, json, unicodedata, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_FILE = os.path.join(ROOT, 'all_data.json')
OUT_FILE = os.path.join(ROOT, 'core', 'fixtures', 'structure_candidates_aggressive.json')
CLEANED = os.path.join(ROOT, 'cleaned_partial_all_data.json')

keywords = ['Commissariat','Mairie','Gendarmerie','Poste','Police','Centre','Station','Bureau de poste']
kw_re = re.compile(r'(' + '|'.join([re.escape(k) for k in keywords]) + r')', re.IGNORECASE)
email_re = re.compile(r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}')
phone_re = re.compile(r'(\+?\d[\d \-\(\)]{6,}\d)')


def normalize_name(name):
    if not name: return ''
    n = unicodedata.normalize('NFKD', name)
    n = ''.join(ch for ch in n if not unicodedata.combining(ch))
    return n.strip().lower()


def extract():
    with open(DATA_FILE, 'r', encoding='utf-16', errors='replace') as f:
        s = f.read()

    cands = {}

    # extract explicit structure objects
    for m in re.finditer(r'"model"\s*:\s*"core\.structurelocale"', s):
        obj_start = s.rfind('{', 0, m.start())
        if obj_start == -1: continue
        depth = 0; i = obj_start; end = None
        while i < len(s):
            if s[i] == '{': depth += 1
            elif s[i] == '}': depth -= 1
            i += 1
            if depth == 0:
                end = i
                break
        if end is None: continue
        ctx = s[obj_start:end]
        q = re.search(r'"nom"\s*:\s*"(?P<name>[^"\\]{3,200})"', ctx)
        name = q.group('name').strip() if q else None
        pref = re.search(r'"prefecture"\s*:\s*(?P<pref>\d+)', ctx)
        pref_id = int(pref.group('pref')) if pref else None
        email = email_re.search(ctx)
        phone = phone_re.search(ctx)
        key = name if name else ('struct_'+str(len(cands)))
        norm = normalize_name(key)
        if norm not in cands:
            cands[norm] = {'name':name,'source':'structure_model','pref_id':pref_id,'email': email.group(0) if email else None,'phone': phone.group(0) if phone else None,'context':ctx[:400],'confidence':'high' if name else 'medium'}

    # keyword-based scanning
    for m in kw_re.finditer(s):
        start = max(0, m.start()-80)
        end = min(len(s), m.end()+200)
        ctx = s[start:end]
        q = re.search(r'"(?P<q>[^"\\]{6,200})"', ctx)
        name = None
        if q:
            cand = q.group('q').strip()
            if len(cand) > 5 and not re.match(r'^(nom|type_structure|email|adresse)$', cand, re.I):
                name = cand
        else:
            m2 = re.search(r'((?:Commissariat|Mairie|Gendarmerie|Poste|Police|Station|Centre)[^,\n]{0,80})', ctx, re.I)
            if m2:
                name = m2.group(1).strip()
        if name:
            norm = normalize_name(name)
            if norm not in cands:
                email = email_re.search(ctx)
                phone = phone_re.search(ctx)
                pref=None
                m_pref = re.search(r'"prefecture"\s*:\s*(?P<pref>\d+)', ctx)
                if m_pref: pref=int(m_pref.group('pref'))
                cands[norm] = {'name':name,'source':'keyword','pref_id':pref,'email': email.group(0) if email else None,'phone': phone.group(0) if phone else None,'context':ctx,'confidence':'medium' if pref else 'low'}

    # email-only and phone-only near keywords
    for em in email_re.finditer(s):
        st=max(0, em.start()-60); ed=min(len(s),em.end()+60)
        ctx = s[st:ed]
        if kw_re.search(ctx):
            q = re.search(r'"(?P<q>[^"\\]{6,200})"', ctx)
            name = q.group('q').strip() if q else None
            key = (name if name else em.group(0))
            norm = normalize_name(key)
            if norm not in cands:
                cands[norm] = {'name':name,'source':'email','pref_id':None,'email': em.group(0),'phone':None,'context':ctx,'confidence':'low'}

    for ph in phone_re.finditer(s):
        st=max(0, ph.start()-60); ed=min(len(s),ph.end()+60)
        ctx=s[st:ed]
        if kw_re.search(ctx):
            q = re.search(r'"(?P<q>[^"\\]{6,200})"', ctx)
            name = q.group('q').strip() if q else None
            key = (name if name else ph.group(0))
            norm = normalize_name(key)
            if norm not in cands:
                cands[norm] = {'name':name,'source':'phone','pref_id':None,'email':None,'phone': ph.group(0),'context':ctx,'confidence':'low'}

    # map pref ids to names if possible
    pref_map={}
    try:
        with open(CLEANED,'r',encoding='utf-8') as fh:
            parsed=json.load(fh)
        for o in parsed:
            if o.get('model')=='core.prefecture':
                pref_map[o.get('pk')] = o.get('fields',{}).get('nom')
    except Exception:
        pref_map={}

    out=[]
    for k,v in cands.items():
        if v.get('pref_id') and v['pref_id'] in pref_map:
            v['pref_name'] = pref_map[v['pref_id']]
        else:
            v['pref_name'] = None
        out.append(v)

    out.sort(key=lambda x: (0 if x['confidence']=='high' else 1, x['name'] or ''))

    with open(OUT_FILE, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    print('Wrote', OUT_FILE, 'with', len(out), 'candidates')

if __name__=='__main__':
    extract()
