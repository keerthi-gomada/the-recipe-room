import re
ALIASES={'eggs':'egg','potatoes':'potato','tomatoes':'tomato','chillies':'chilli','chilies':'chilli','chili':'chilli','capsicum':'pepper','brinjal':'eggplant','aubergine':'eggplant','ladyfinger':'okra','bhindi':'okra','palak':'spinach'}
def words(text):
    result=set()
    for word in re.findall(r'[a-z]+',text.lower().replace('_',' ')):
        word=ALIASES.get(word,word)
        if len(word)>3 and word.endswith('s') and not word.endswith(('ss','us')): word=word[:-1]
        result.add(word)
    return result

def ingredient_catalog(recipes):
    names=set()
    for recipe in recipes:
        for line in [*recipe.get('ingredients',[]), *recipe.get('cleaned_ingredients',[])]:
            name=re.split(r'\s+[-–]\s+',line,maxsplit=1)[0].strip()
            name=re.sub(r'^[\d\s./¼½¾⅓⅔⅛⅜⅝⅞–-]+','',name)
            name=re.sub(r'^(?:(?:cups?|tablespoons?|teaspoons?|tbsp|tsp|grams?|g|kg|ml|litres?|liters?|inches?|inch|cloves?|sprigs?|pieces?|large|small|medium|whole)\s+)+','',name,flags=re.I).strip()
            if name and words(name): names.add(name.lower())
    return sorted(names)

class CollectionSearch:
    def __init__(self,recipes):
        self.ingredients=[words(' '.join([*r.get('ingredients',[]), *r.get('cleaned_ingredients',[])])) for r in recipes]
        self.titles=[words(r.get('title','')) for r in recipes]
        self.cuisines=[words(r.get('cuisine','')) for r in recipes]
    def rank(self,query,cuisine_names,semantic_ids,limit):
        text=query.lower().replace('_',' ')
        cuisines=set()
        for name in sorted(cuisine_names,key=len,reverse=True):
            pattern=r'\b'+re.escape(name)+r'\b'
            if re.search(pattern,text):
                cuisines |= words(name)
                text=re.sub(pattern,' ',text)
        terms=words(text)-{'recipe','with','and','of','the'}
        if not terms:return list(semantic_ids)[:limit]
        order={int(idx):i for i,idx in enumerate(semantic_ids)}
        matches=[]
        for idx,ingredients in enumerate(self.ingredients):
            ingredient_match=terms<=ingredients
            if ingredient_match or terms<=self.titles[idx]:
                matches.append((idx,ingredient_match,len(cuisines & self.cuisines[idx])))
        matches.sort(key=lambda row:(-row[1],-row[2],order.get(row[0],len(semantic_ids)),row[0]))
        return [row[0] for row in matches[:limit]]
