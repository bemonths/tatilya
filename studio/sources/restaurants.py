"""Visit South Walton Restaurants directory: HTML filters, cards and detail pages."""
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit, urljoin, parse_qsl, urlencode, unquote

import httpx

from .base import CollectionResult, SourceError, CollectionCanceled
from .html_tree import Tree, Node
from .url_identity import https_source_identity
from ..regions import REGIONS

SOURCE_URL = 'https://www.visitsouthwalton.com/listings/culinary-experiences/'
HOSTS = {'www.visitsouthwalton.com', 'visitsouthwalton.com'}
SOURCE_HOST_ALIASES = {host: 'visitsouthwalton.com' for host in HOSTS}
SOURCE_IDENTITY = https_source_identity(SOURCE_URL, host_aliases=SOURCE_HOST_ALIASES)
REGION_MAP = {name: identifier for identifier, name in REGIONS}
EXCLUDED = {'Miramar Beach', 'Seascape', 'Sandestin'}
MAX_BYTES, MAX_PAGES, MAX_DETAILS = 5_000_000, 100, 500
RETRY_SECONDS, REQUEST_GAP = 0.5, 0.1


def clean(value): return ' '.join(value.split())


def checked_url(value, base=SOURCE_URL):
    try:
        if not isinstance(value,str) or any(ord(c)<32 for c in value) or '\\' in value: raise ValueError()
        parts=urlsplit(urljoin(base,value))
        if parts.scheme!='https' or parts.hostname not in HOSTS or parts.username is not None or parts.password is not None or parts.port not in (None,443):raise ValueError()
        return urlunsplit(('https',parts.hostname,parts.path or '/',parts.query,''))
    except ValueError as exc:
        raise SourceError('Restoran kaynağı geçersiz veya izin verilmeyen bir adres döndürdü. İstek yapılmadı.') from exc


def identity(url):
    parts=urlsplit(checked_url(url))
    path=unquote(parts.path)
    if not re.fullmatch(r'/listing/[A-Za-z0-9_-]+/?',path):
        raise SourceError('Restoran detay adresinin yapısı değişti.')
    return path.rstrip('/')+'/'


def one(nodes, message):
    if len(nodes)!=1: raise SourceError(message)
    return nodes[0]


def parse_filters(content):
    tree=Tree(content).root
    candidates=[]
    for form in tree.find('form'):
        selects=form.find('select')
        for select in selects:
            labels=[clean(o.text()) for o in select.find('option')]
            if set(REGION_MAP).issubset(labels): candidates.append((form,select))
    form,neighborhood=one(candidates,'Restoran mahalle filtresi değişti; 13 hedef mahalle bulunamadı.')
    business=one([s for s in form.find('select') if 'Restaurants' in [clean(o.text()) for o in s.find('option')]],'Restaurants işletme türü filtresi bulunamadı.')
    def options(select):
        result={}
        for option in select.find('option'):
            label=clean(option.text());value=option.attrs.get('value')
            if value:
                if label in result or value in [v['value'] for v in result.values()]:raise SourceError('Restoran filtre seçenekleri tekrarlı.')
                result[label]={'value':value,'selected':'selected' in option.attrs}
        return result
    n,b=options(neighborhood),options(business)
    if 'Restaurants' not in b:raise SourceError('Restaurants işletme türü filtre değeri eksik.')
    if not (set(REGION_MAP)|EXCLUDED).issubset(n): raise SourceError('Restoran mahalle filtre yapısı beklenenden farklı.')
    names=[neighborhood.attrs.get('name'),business.attrs.get('name')]
    if any(not n or not re.fullmatch(r'[A-Za-z0-9_\[\]-]+',n) for n in names) or names[0]==names[1]:raise SourceError('Restoran filtre parametreleri geçersiz.')
    action=checked_url(form.attrs.get('action') or SOURCE_URL)
    if urlsplit(action).path!=urlsplit(SOURCE_URL).path or form.attrs.get('method','get').lower()!='get':raise SourceError('Restoran filtre formunun hedefi değişti.')
    return {'url':action,'neighborhood_param':names[0],'business_param':names[1],'neighborhoods':n,'business':b['Restaurants'],
            'selected_businesses':[label for label,option in b.items() if option['selected']]}


def listing_url(filters, neighborhood):
    return filters['url']+'?'+urlencode({filters['neighborhood_param']:filters['neighborhoods'][neighborhood]['value'],filters['business_param']:filters['business']['value']})


def normalized_page(url):
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc,p.path,urlencode(sorted(parse_qsl(p.query,keep_blank_values=True))),''))


def parse_listing(content, url, filters, neighborhood):
    actual=parse_filters(content)
    if actual['neighborhood_param']!=filters['neighborhood_param'] or actual['business_param']!=filters['business_param'] or actual['neighborhoods'][neighborhood]['value']!=filters['neighborhoods'][neighborhood]['value'] or actual['business']['value']!=filters['business']['value']:
        raise SourceError('Restoran filtre değerleri çekim sırasında değişti.')
    if (not actual['neighborhoods'][neighborhood]['selected']
            or sum(option['selected'] for option in actual['neighborhoods'].values()) != 1
            or actual['selected_businesses'] != ['Restaurants']):
        raise SourceError('Kaynak istenen mahalle/Restaurants filtresini uygulamadı.')
    tree=Tree(content).root
    cards=[]
    decks=tree.find(cls='card-deck')
    if not decks:raise SourceError('Restoran sonuç listesinin yapısı değişti.')
    for deck in decks:
        for link in deck.find('a'):
            if not link.find(cls='card-inner'):continue
            title=one(link.find('h5'),'Restoran kartında ad eksik.');name=clean(title.text())
            if not name:raise SourceError('Restoran kartında ad boş.')
            detail=checked_url(link.attrs.get('href',''),url)
            cards.append({'external_id':identity(detail),'name':name,'listing_url':urlunsplit(('https','www.visitsouthwalton.com',identity(detail),'',''))})
    if not cards and not re.search(r'no (?:results|listings|businesses)(?: found)?',clean(tree.text()),re.I):
        raise SourceError('Restoran sonuç yapısı değişti veya boş sonuç doğrulanamadı.')
    pages=[];next_pages=[]
    fixed={filters['neighborhood_param']:filters['neighborhoods'][neighborhood]['value'],filters['business_param']:filters['business']['value']}
    for pager in tree.find(cls='pager'):
        for link in pager.find('a'):
            target=checked_url(link.attrs.get('href',''),url);parts=urlsplit(target)
            if parts.path!=urlsplit(SOURCE_URL).path:raise SourceError('Restoran sayfalama adresi dizin dışına çıktı.')
            query=dict(parse_qsl(parts.query,keep_blank_values=True))
            if any(k in query and query[k]!=v for k,v in fixed.items()):raise SourceError('Sayfalama restoran filtresini değiştirdi.')
            query.update(fixed)
            target=normalized_page(urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(query),'')))
            if 'active' not in link.attrs.get('class','').split():pages.append(target)
            if link.parent and 'next' in link.parent.attrs.get('class','').split():next_pages.append(target)
    return cards,list(dict.fromkeys(pages)),next_pages


def parse_detail(content,url,neighborhoods):
    tree=Tree(content).root
    hero=one(tree.find(id='listing-hero'),'Restoran detay sayfasının yapısı değişti.')
    name=clean(one(hero.find('h1'),'Restoran adı bulunamadı.').text())
    if not name:raise SourceError('Restoran adı boş.')
    description_nodes=hero.find(cls='description')
    if len(description_nodes)>1:
        raise SourceError('Restoran açıklama alanının yapısı belirsiz; birden fazla blok bulundu.')
    description=None
    if description_nodes:
        description=clean(' '.join(c.text() if isinstance(c,Node) else c for c in description_nodes[0].children if not isinstance(c,Node) or c.tag not in ('h5','script','style'))) or None
    regions=[]
    for region in sorted(set(neighborhoods)):
        if region not in REGION_MAP:raise SourceError('Restoran mahallesi kapsam dışında veya eşlenemiyor.')
        regions.append({'source_neighborhood':region,'canonical_region_id':REGION_MAP[region]})
    if not regions:raise SourceError('Restoran mahalle provenance bilgisi eksik.')
    cuisines,meals,amenities=[],[],[]
    for block in hero.find(cls='amenities'):
        for item in block.find('li'):
            entry=clean(item.text())
            label,sep,rest=entry.partition(':')
            if label.strip() in ('Cuisine','Meals Served') and sep:
                values=[clean(v) for v in rest.split(',') if clean(v)]
                (cuisines if label.strip()=='Cuisine' else meals).extend(values)
            elif entry:amenities.append(entry)
    details=one(hero.find(cls='details'),'Restoran iletişim/adres alanının yapısı değişti.')
    address=[];taking=False
    for child in details.children:
        if isinstance(child,Node) and child.tag in ('h5','h6'):
            taking=clean(child.text())=='Address';continue
        if taking:address.append(child.text() if isinstance(child,Node) else child)
    lines=[clean(v) for v in ''.join(address).splitlines() if clean(v)]
    city=state=postal=None
    if lines:
        match=re.fullmatch(r'(.+?),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)',lines[-1])
        if match:city,state,postal=match.groups();lines.pop()
    phone=email=website=None
    for link in hero.find('a'):
        href=link.attrs.get('href') or ''
        if href.lower().startswith('tel:'):phone=clean(link.text()) or unquote(href[4:]) or None
        if href.lower().startswith('mailto:'):email=clean(unquote(href[7:].split('?')[0])) or None
        if clean(link.text()).casefold()=='visit website':
            try:
                p=urlsplit(urljoin(url,href))
                if p.scheme not in ('http','https') or not p.hostname or p.username is not None or p.password is not None:raise ValueError()
                website=urlunsplit(p)
            except ValueError as exc:raise SourceError('Restoran web sitesi adresi geçersiz.') from exc
    return {'external_id':identity(url),'name':name,'listing_url':checked_url(identity(url)),
            'description':description,'address_line_1':lines[0] if lines else None,
            'address_line_2':clean(' '.join(lines[1:])) or None,'city':city,'state':state,'postal_code':postal,
            'phone':phone,'email':email,'website_url':website,'cuisines':sorted(set(cuisines)),
            'meals_served':sorted(set(meals)),'amenities':sorted(set(amenities)),
            'source_neighborhoods':[r['source_neighborhood'] for r in regions],'regions':regions}


def check(canceled):
    if canceled():raise CollectionCanceled()


def pause(seconds,canceled):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        check(canceled);time.sleep(min(0.05,max(0,end-time.monotonic())))


class Reader:
    def __init__(self,client,path,canceled):
        self.client,self.path,self.canceled=client,path,canceled
        self.manifest={'connector':'south-walton-restaurants/1','source_url':SOURCE_URL,'responses':[]}
    def save(self,requested,response,body,kind,neighborhood):
        sequence=len(self.manifest['responses'])+1
        relative=f"{'detail' if kind=='detail' else 'listing'}/{sequence:04d}.html"
        target=self.path.parent/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
        stamp=datetime.now(timezone.utc).isoformat()
        self.manifest['fetched_at']=stamp
        self.manifest['responses'].append({'sequence':sequence,'request_kind':kind,'neighborhood':neighborhood,
            'requested_url':requested,'final_url':str(response.url),'status':response.status_code,
            'content_type':response.headers.get('content-type'),'fetched_at':stamp,'raw_file':relative,
            'raw_sha256':hashlib.sha256(body).hexdigest()})
        temporary=self.path.with_suffix('.tmp');temporary.write_text(json.dumps(self.manifest,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(self.path)
    def get(self,url,kind,neighborhood=None):
        original=checked_url(url)
        for attempt in range(2):
            current=original
            try:
                for hop in range(4):
                    check(self.canceled);pause(REQUEST_GAP,self.canceled)
                    with self.client.stream('GET',current,follow_redirects=False,headers={'User-Agent':'30AStudio/0.5 (+https://github.com/bemonths/tatilya)','Accept':'text/html'}) as response:
                        chunks=[];size=0
                        for part in response.iter_bytes():
                            check(self.canceled);size+=len(part)
                            if size>MAX_BYTES:raise SourceError('Restoran yanıtı boyut sınırını aştı.')
                            chunks.append(part)
                        body=b''.join(chunks);self.save(current,response,body,kind,neighborhood)
                        if response.status_code in (301,302,303,307,308):
                            if hop==3 or not response.headers.get('location'):raise SourceError('Restoran yönlendirme sınırı aşıldı veya hedef eksik.')
                            current=checked_url(response.headers['location'],current);continue
                        if response.status_code==429:raise SourceError('Restoran kaynağı istek sınırına ulaştı (429). Daha sonra deneyin.')
                        if response.status_code>=500:
                            if attempt==0:break
                            raise SourceError('Restoran kaynağı sunucu hatası döndürdü; daha sonra deneyin.')
                        if response.status_code!=200:raise SourceError(f'Restoran kaynağı okunamadı (HTTP {response.status_code}).')
                        if response.headers.get('content-type','').split(';')[0].strip().lower() not in ('text/html','application/xhtml+xml'):raise SourceError('Restoran kaynağı beklenen HTML içerik türünü döndürmedi.')
                        try:return body.decode('utf-8-sig'),str(response.url)
                        except UnicodeError as exc:raise SourceError('Restoran HTML karakter kodlaması geçersiz.') from exc
            except (httpx.NetworkError,httpx.TimeoutException) as exc:
                if attempt==1:raise SourceError('Restoran bağlantısı kurulamadı veya zaman aşımı oluştu.') from exc
            except httpx.HTTPError as exc:raise SourceError('Restoran HTTP yanıtı geçersiz.') from exc
            pause(RETRY_SECONDS,self.canceled)
        raise SourceError('Restoran isteği tamamlanamadı.')


def collect(raw_path,progress,canceled,*,client=None):
    own=client is None;client=client or httpx.Client(timeout=httpx.Timeout(20,connect=10),verify=True)
    reader=Reader(client,raw_path,canceled)
    try:
        content,_=reader.get(SOURCE_URL,'filters');filters=parse_filters(content)
        candidates={};page_count=duplicates=0;counts={}
        for index,neighborhood in enumerate(REGION_MAP):
            progress(5+index*3,f'{neighborhood} · Restaurants dizini okunuyor.')
            pending=[normalized_page(listing_url(filters,neighborhood))];seen=set();region_ids=set()
            while pending:
                check(canceled);url=pending.pop(0)
                if url in seen:continue
                if page_count>=MAX_PAGES:raise SourceError('Restoran sayfalama üst sınırı aşıldı.')
                seen.add(url);content,final=reader.get(url,'listing',neighborhood);page_count+=1
                # A redirect must not silently drop or change the two selected filters.
                cards,pages,next_pages=parse_listing(content,final,filters,neighborhood)
                if any(p in seen for p in next_pages):raise SourceError('Restoran sayfalamasında döngü tespit edildi.')
                pending.extend(p for p in pages if p not in seen and p not in pending)
                for card in cards:
                    identifier=card['external_id'];region_ids.add(identifier)
                    if identifier in candidates:
                        if candidates[identifier]['name']!=card['name']:raise SourceError('Aynı restoran kimliği farklı adlarla bulundu.')
                        duplicates+=1;candidates[identifier]['neighborhoods'].add(neighborhood)
                    else:candidates[identifier]={**card,'neighborhoods':{neighborhood}}
                    if len(candidates)>MAX_DETAILS:raise SourceError('Restoran detay üst sınırı aşıldı.')
            counts[neighborhood]=len(region_ids)
        records=[]
        for index,card in enumerate(candidates.values()):
            check(canceled);progress(45+int(45*index/max(1,len(candidates))),f"Restoran ayrıntısı {index+1}/{len(candidates)} · {card['name']}")
            content,final=reader.get(card['listing_url'],'detail',sorted(card['neighborhoods']))
            if identity(final)!=card['external_id']:raise SourceError('Restoran detay yönlendirmesi kaynak kimliğini değiştirdi.')
            record=parse_detail(content,final,card['neighborhoods'])
            if record['name']!=card['name']:raise SourceError('Restoran kartı ile detay adı uyuşmuyor; kimlik doğrulanamadı.')
            records.append(record)
        check(canceled)
        if not records:raise SourceError('13 hedef mahallede restoran bulunamadı; kaynak yapısını kontrol edin.')
        metadata={'target_neighborhood_count':len(REGION_MAP),'listing_page_count':page_count,
                  'unique_restaurant_count':len(records),'detail_page_count':len(records),'duplicate_count':duplicates,
                  'neighborhood_counts':counts,'business_type':'Restaurants','excluded_neighborhoods':sorted(EXCLUDED),
                  'filters':filters,'represented_neighborhood_count':sum(bool(c) for c in counts.values()),
                  'cuisine_count':len({c for r in records for c in r['cuisines']}),
                  'description_missing_count':sum(record['description'] is None for record in records)}
        return CollectionResult(records,len(records),0,None,metadata)
    finally:
        if own:client.close()


class RestaurantsConnector:
    name='south-walton-restaurants';version='south-walton-restaurants/1';method='HTML';diff_enabled=True
    raw_filename='manifest.json'
    def supports(self,source):
        return https_source_identity(source['url'], host_aliases=SOURCE_HOST_ALIASES) == SOURCE_IDENTITY
    def collect(self,source,raw_path,progress,canceled):return collect(raw_path,progress,canceled)
    def store_records(self,con,run_id,records,related=None):
        for record in records:
            row={k:v for k,v in record.items() if k not in ('regions','source_neighborhoods')}
            for key in ('cuisines','meals_served','amenities'):row[key]=json.dumps(row[key],ensure_ascii=False)
            fields=['run_id',*row]
            con.execute(f"INSERT INTO restaurant_records ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",[run_id,*row.values()])
            con.executemany('INSERT INTO restaurant_regions VALUES (?,?,?,?)',[(run_id,record['external_id'],r['source_neighborhood'],r['canonical_region_id']) for r in record['regions']])
    def read_records(self,con,run_id):
        records=[]
        for row in con.execute('SELECT * FROM restaurant_records WHERE run_id=? ORDER BY name,external_id',(run_id,)):
            record=dict(row)
            for key in ('cuisines','meals_served','amenities'):record[key]=json.loads(record[key])
            record['regions']=[dict(r) for r in con.execute('SELECT source_neighborhood,canonical_region_id FROM restaurant_regions WHERE run_id=? AND external_id=? ORDER BY source_neighborhood',(run_id,record['external_id']))]
            record['source_neighborhoods']=[r['source_neighborhood'] for r in record['regions']];records.append(record)
        return records
    def comparison_value(self,record):
        fields=('name','description','address_line_1','address_line_2','city','state','postal_code','phone','email','website_url')
        return {**{key:record[key] for key in fields},**{key:sorted(set(record[key])) for key in ('cuisines','meals_served','amenities')},
                'regions':sorted((r['source_neighborhood'],r['canonical_region_id']) for r in record['regions'])}
