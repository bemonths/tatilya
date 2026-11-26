"""Visit South Walton Restaurants directory: HTML filters, cards and detail pages.

HEDEF-01 (26 Nov 2026): visitsouthwalton.com was rebuilt with Gatsby; the directory page has no filter form or cards any more.
The page asks the site's own public JSON API for its listings (`/api/simpleview/listing/all/`, plain GET; the user approved reading
it on 26 Nov 2026). When the directory page is the rebuilt one, the collector reads the same API: the site's neighbourhood list
(`/api/beach/neighborhood/all/`) gives the target neighbourhoods' permalinks, then the listings of sub-category "restaurants" in
those 13 neighbourhoods. Each listing's neighbourhood is its own `Neighborhood` relation; cuisines, meals and amenities are only
what the listing's `amenities` (and `cuisines` / `mealTypes`) say. Every answer is kept with the manifest.
"""
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
from ..destinations.thirty_a import NEIGHBORHOOD_ALIASES, REGIONS

SOURCE_URL = 'https://www.visitsouthwalton.com/listings/culinary-experiences/'
VERSION = 'south-walton-restaurants/3'      # /2: a city line without a ZIP code is parsed as city and state; /3: the rebuilt site's API
HOSTS = {'www.visitsouthwalton.com', 'visitsouthwalton.com'}
SOURCE_HOST_ALIASES = {host: 'visitsouthwalton.com' for host in HOSTS}
SOURCE_IDENTITY = https_source_identity(SOURCE_URL, host_aliases=SOURCE_HOST_ALIASES)
REGION_MAP = {name: identifier for identifier, name in REGIONS}
EXCLUDED = {'Miramar Beach', 'Seascape', 'Sandestin'}
MAX_BYTES, MAX_PAGES, MAX_DETAILS = 5_000_000, 100, 500
RETRY_SECONDS, REQUEST_GAP = 0.5, 0.1
# HEDEF-01: the rebuilt site's own API (the same addresses and parameters its directory page sends; one page of 200 holds them all)
API_ROOT = 'https://www.visitsouthwalton.com/api/'
API_GAP, API_PAGE_SIZE, MAX_API_BYTES = 8.0, 200, 30_000_000
CATEGORY_PERMALINK, SUBCATEGORY_PERMALINK = 'culinary-experiences', 'restaurants'
GATSBY_MARK = re.compile(r'<div\s+id="___gatsby"')
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')


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
        # The city line, with or without a ZIP code ("Inlet Beach, FL" is published without one).
        match=re.fullmatch(r'(.+?),\s*([A-Z]{2})(?:\s+(\d{5}(?:-\d{4})?))?',lines[-1])
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


# --- HEDEF-01: the rebuilt site's own JSON API ---------------------------------------------------------------------------------

def neighborhood_api_url():
    return API_ROOT+'beach/neighborhood/all/?_sort=sort&_lang=en&_joinLang=en'


def listing_api_url(permalinks,page):
    # The parameters the directory page itself sends (sorted by name so the pages are stable; embeddings left out of the answer).
    query=['approved=true','deleted=false','archived=false','_join=true',f'page={int(page)}',f'pageSize={API_PAGE_SIZE}','_sort=name','_order=ASC',
           '_exclude=embeddings',f'Category.permalink={CATEGORY_PERMALINK}','Neighborhood.permalink='+','.join(permalinks),
           f'SubCategory.permalink={SUBCATEGORY_PERMALINK}','_lang=en','_joinLang=en']
    return API_ROOT+'simpleview/listing/all/?'+'&'.join(query)


def api_rows(answer,what):
    if not isinstance(answer,dict) or answer.get('errorCode') or answer.get('errorMessage') or not isinstance(answer.get('data'),list):
        raise SourceError(f'Sitenin {what} cevabı beklenen biçimde değil; site yapısı değişmiş olabilir.')
    if any(not isinstance(row,dict) for row in answer['data']):raise SourceError(f'Sitenin {what} cevabında beklenmeyen bir kayıt var.')
    return answer['data']


def region_of(name,region_map):
    name=clean(name) if isinstance(name,str) else ''
    return name if name in region_map else NEIGHBORHOOD_ALIASES.get(name) if NEIGHBORHOOD_ALIASES.get(name) in region_map else None


def api_permalinks(answer,region_map):
    """{target neighbourhood: the site's permalink} from the site's neighbourhood list (exact name or the profile's alias)."""
    found={}
    for row in api_rows(answer,'mahalle listesi'):
        region=region_of(row.get('name'),region_map);permalink=row.get('permalink')
        if region is None:continue
        if not isinstance(permalink,str) or not SLUG.fullmatch(permalink):raise SourceError('Sitenin mahalle listesinde geçersiz bir sayfa bağlantısı (permalink) var.')
        if region in found:raise SourceError(f'Sitenin mahalle listesinde aynı hedef mahalle iki kez geçiyor: {region}.')
        found[region]=permalink
    missing=[name for name in region_map if name not in found]
    if missing:raise SourceError(f"Hedef mahalle sitenin mahalle listesinde bulunamadı: {', '.join(missing)}. Önceki kayıtlar korundu.")
    return {name:found[name] for name in region_map}


def text_of(value):
    if not isinstance(value,str):return None
    if '<' in value:value=Tree(value).root.text()
    return clean(value) or None


def website(value):
    """The listing's web address as the site's own link shows it: a bare domain gets 'https://' (the site's link component does the same)."""
    value=text_of(value)
    if not value:return None,False
    added=not re.match(r'https?://',value,re.I)
    try:
        parts=urlsplit(('https://'+value) if added else value)
        if parts.scheme.lower() not in ('http','https') or not parts.hostname or parts.username is not None or parts.password is not None:raise ValueError()
    except ValueError as exc:raise SourceError('Restoran web sitesi adresi geçersiz.') from exc
    return urlunsplit(parts),added


def api_amenities(row):
    """(cuisines, meals served, other amenities) exactly as the listing lists them; nothing listed stays empty."""
    cuisines=[clean(v) for v in row.get('cuisines') or [] if isinstance(v,str) and clean(v)]
    meals=[clean(v) for v in row.get('mealTypes') or [] if isinstance(v,str) and clean(v)]
    other=[]
    entries=row.get('amenities') or []
    if not isinstance(entries,list) or any(not isinstance(e,dict) for e in entries):raise SourceError('Restoran kaydının olanak listesi okunamadı.')
    for entry in entries:
        for key,value in entry.items():
            label=clean(str(key))
            if not label or value is None or value is False or value==0 or value=='' or value==[]:continue
            if label in ('Cuisine','Meals Served'):
                values=value if isinstance(value,list) else [value]
                (cuisines if label=='Cuisine' else meals).extend(clean(str(v)) for v in values if clean(str(v)))
            elif value is True or value==1:other.append(label)
            elif isinstance(value,list):other.append(f"{label}: {', '.join(clean(str(v)) for v in value if clean(str(v)))}")
            elif isinstance(value,str) and re.match(r'https?://',value.strip(),re.I):other.append(label)     # a link ("View Menu"): its label
            else:other.append(f'{label}: {clean(str(value))}')
    return sorted(set(cuisines)),sorted(set(meals)),sorted(set(other))


def parse_api_listing(row,region_map):
    uri=row.get('uri')
    if not isinstance(uri,str):raise SourceError('Restoran kaydında sayfa adresi (uri) yok.')
    external=identity(uri)
    name=text_of(row.get('companyName'))
    if not name:raise SourceError('Restoran kaydında ad eksik.')
    subcategories={(item.get('object') or {}).get('permalink') for item in row.get('SubCategory') or [] if isinstance(item,dict)}
    if SUBCATEGORY_PERMALINK not in subcategories:raise SourceError('Site Restaurants dışında bir işletme döndürdü; filtre uygulanmamış olabilir.')
    regions=set()
    for item in row.get('Neighborhood') or []:
        region=region_of((item.get('object') or {}).get('name') if isinstance(item,dict) else None,region_map)
        if region:regions.add(region)
    if not regions:raise SourceError(f'{name}: restoranın mahalle bilgisi hedef mahallelerden birine bağlanmıyor.')
    cuisines,meals,amenities=api_amenities(row)
    site,added=website(row.get('url'))
    return {'external_id':external,'name':name,'listing_url':checked_url(external),'description':text_of(row.get('description')),
            'address_line_1':text_of(row.get('address1')),'address_line_2':text_of(row.get('address2')),'city':text_of(row.get('city')),
            'state':text_of(row.get('state')),'postal_code':text_of(row.get('zip')),'phone':text_of(row.get('phone')),
            'email':text_of(row.get('email')),'website_url':site,'cuisines':cuisines,'meals_served':meals,'amenities':amenities,
            'source_neighborhoods':sorted(regions),'regions':[{'source_neighborhood':n,'canonical_region_id':region_map[n]} for n in sorted(regions)]},added


def collect_api(reader,progress,canceled,region_map):
    progress(5,'Site yenilenmiş: sitenin kendi mahalle listesi okunuyor (API).')
    answer,_=reader.get(neighborhood_api_url(),'api-neighborhoods')
    permalinks=api_permalinks(answer,region_map)
    rows,page,pages,total=[],1,1,None
    while page<=pages:
        check(canceled)
        if page>MAX_PAGES:raise SourceError('Restoran sayfalama üst sınırı aşıldı.')
        progress(10+min(30,page*5),f'Restaurants listesi okunuyor (API, sayfa {page}).')
        answer,_=reader.get(listing_api_url(list(permalinks.values()),page),'api-listings')
        rows.extend(api_rows(answer,'restoran listesi'))
        if type(answer.get('pages')) is not int or type(answer.get('total')) is not int or answer['pages']<0:
            raise SourceError('Sitenin restoran listesinde sayfa bilgisi yok; site yapısı değişmiş olabilir.')
        if total is not None and (answer['total']!=total or answer['pages']!=pages):raise SourceError('Sitenin restoran listesi sayfalar arasında değişti; daha sonra yeniden deneyin.')
        total,pages=answer['total'],answer['pages'];page+=1
    if len(rows)!=total:raise SourceError('Sitenin restoran listesindeki kayıt sayısı bildirilen toplamla uyuşmuyor.')
    if len(rows)>MAX_DETAILS:raise SourceError('Restoran detay üst sınırı aşıldı.')
    records,seen,added=[],{},0
    for row in rows:
        check(canceled)
        record,scheme=parse_api_listing(row,region_map)
        if record['external_id'] in seen:
            if seen[record['external_id']]['name']!=record['name']:raise SourceError('Aynı restoran kimliği farklı adlarla bulundu.')
            raise SourceError('Sitenin restoran listesinde aynı restoran iki kez geçiyor.')
        seen[record['external_id']]=record;records.append(record);added+=scheme
    if not records:raise SourceError('13 hedef mahallede restoran bulunamadı; kaynak yapısını kontrol edin.')
    counts={name:sum(name in r['source_neighborhoods'] for r in records) for name in region_map}
    metadata={'target_neighborhood_count':len(region_map),'listing_page_count':pages,
              'unique_restaurant_count':len(records),'detail_page_count':0,'duplicate_count':0,
              'neighborhood_counts':counts,'business_type':'Restaurants','excluded_neighborhoods':sorted(EXCLUDED),
              'filters':{'api':API_ROOT+'simpleview/listing/all/','category':CATEGORY_PERMALINK,'subcategory':SUBCATEGORY_PERMALINK,
                         'neighborhood_permalinks':permalinks},
              'represented_neighborhood_count':sum(bool(c) for c in counts.values()),
              'cuisine_count':len({c for r in records for c in r['cuisines']}),
              'description_missing_count':sum(record['description'] is None for record in records),
              'kaynak_bicimi':'simpleview-api','source_total':total,'website_scheme_added_count':added}
    progress(95,f'{len(records)} restoran okundu (13 hedef mahalle, sitenin API\'si).')
    return CollectionResult(records,len(records),0,None,metadata)


def check(canceled):
    if canceled():raise CollectionCanceled()


def pause(seconds,canceled):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        check(canceled);time.sleep(min(0.05,max(0,end-time.monotonic())))


class Reader:
    def __init__(self,client,path,canceled):
        self.client,self.path,self.canceled=client,path,canceled
        self.manifest={'connector':VERSION,'source_url':SOURCE_URL,'responses':[]}
    def save(self,requested,response,body,kind,neighborhood):
        sequence=len(self.manifest['responses'])+1
        relative=f"api/{sequence:04d}.json" if kind.startswith('api') else f"{'detail' if kind=='detail' else 'listing'}/{sequence:04d}.html"
        target=self.path.parent/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
        stamp=datetime.now(timezone.utc).isoformat()
        self.manifest['fetched_at']=stamp
        self.manifest['responses'].append({'sequence':sequence,'request_kind':kind,'neighborhood':neighborhood,
            'requested_url':requested,'final_url':str(response.url),'status':response.status_code,
            'content_type':response.headers.get('content-type'),'fetched_at':stamp,'raw_file':relative,
            'raw_sha256':hashlib.sha256(body).hexdigest()})
        temporary=self.path.with_suffix('.tmp');temporary.write_text(json.dumps(self.manifest,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(self.path)
    def get(self,url,kind,neighborhood=None):
        api=kind.startswith('api')
        original=checked_url(url)
        for attempt in range(2):
            current=original
            try:
                for hop in range(4):
                    check(self.canceled);pause(API_GAP if api else REQUEST_GAP,self.canceled)
                    with self.client.stream('GET',current,follow_redirects=False,headers={'User-Agent':'30AStudio/0.5 (+https://github.com/bemonths/tatilya)','Accept':'application/json' if api else 'text/html'}) as response:
                        chunks=[];size=0
                        for part in response.iter_bytes():
                            check(self.canceled);size+=len(part)
                            if size>(MAX_API_BYTES if api else MAX_BYTES):raise SourceError('Restoran yanıtı boyut sınırını aştı.')
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
                        if api:
                            if response.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':raise SourceError('Sitenin restoran API\'si JSON döndürmedi; site yapısı değişmiş olabilir.')
                            try:return json.loads(body.decode('utf-8-sig')),str(response.url)
                            except (UnicodeError,ValueError) as exc:raise SourceError('Sitenin restoran API cevabı JSON olarak okunamadı.') from exc
                        if response.headers.get('content-type','').split(';')[0].strip().lower() not in ('text/html','application/xhtml+xml'):raise SourceError('Restoran kaynağı beklenen HTML içerik türünü döndürmedi.')
                        try:return body.decode('utf-8-sig'),str(response.url)
                        except UnicodeError as exc:raise SourceError('Restoran HTML karakter kodlaması geçersiz.') from exc
            except (httpx.NetworkError,httpx.TimeoutException) as exc:
                if attempt==1:raise SourceError('Restoran bağlantısı kurulamadı veya zaman aşımı oluştu.') from exc
            except httpx.HTTPError as exc:raise SourceError('Restoran HTTP yanıtı geçersiz.') from exc
            pause(RETRY_SECONDS,self.canceled)
        raise SourceError('Restoran isteği tamamlanamadı.')


def collect(raw_path,progress,canceled,*,client=None,regions=None):
    region_map = REGION_MAP if regions is None else {r["name"]:r["id"] for r in regions}
    if not region_map or not set(region_map).issubset(REGION_MAP):
        raise SourceError("Restoran bölge yapılandırması kaynak kapsamıyla eşleşmiyor.")
    own=client is None;client=client or httpx.Client(timeout=httpx.Timeout(20,connect=10),verify=True)
    reader=Reader(client,raw_path,canceled)
    try:
        content,_=reader.get(SOURCE_URL,'filters')
        if GATSBY_MARK.search(content):return collect_api(reader,progress,canceled,region_map)    # HEDEF-01: the rebuilt site
        filters=parse_filters(content)
        candidates={};page_count=duplicates=0;counts={}
        for index,neighborhood in enumerate(region_map):
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
            for region in record["regions"]:
                region["canonical_region_id"]=region_map[region["source_neighborhood"]]
            records.append(record)
        check(canceled)
        if not records:raise SourceError('13 hedef mahallede restoran bulunamadı; kaynak yapısını kontrol edin.')
        metadata={'target_neighborhood_count':len(region_map),'listing_page_count':page_count,
                  'unique_restaurant_count':len(records),'detail_page_count':len(records),'duplicate_count':duplicates,
                  'neighborhood_counts':counts,'business_type':'Restaurants','excluded_neighborhoods':sorted(EXCLUDED),
                  'filters':filters,'represented_neighborhood_count':sum(bool(c) for c in counts.values()),
                  'cuisine_count':len({c for r in records for c in r['cuisines']}),
                  'description_missing_count':sum(record['description'] is None for record in records)}
        return CollectionResult(records,len(records),0,None,metadata)
    finally:
        if own:client.close()


class RestaurantsConnector:
    name='south-walton-restaurants';version=VERSION;method='HTML';diff_enabled=True
    produces = "restaurant_records"         # the restaurant-sites collector reads the latest run's restaurants
    raw_filename='manifest.json'
    def supports(self,source):
        return source.get('destination_id') == '30a' and https_source_identity(source['url'], host_aliases=SOURCE_HOST_ALIASES) == SOURCE_IDENTITY
    def collect(self,source,raw_path,progress,canceled,*,context):
        return collect(raw_path,progress,canceled,regions=context.canonical_regions)
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
