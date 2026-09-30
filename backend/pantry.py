"""Display-only pantry normalization; recipe quantities remain untouched."""
import re
GROUPS = {
 'Vegetables': 'potato|sweet potato|tomato|onion|spring onion|carrot|cauliflower|broccoli|spinach|eggplant|bell pepper|okra|zucchini|cabbage|red cabbage|pea|green bean|beetroot|radish|pumpkin|bottle gourd|bitter gourd|ridge gourd|ash gourd|drumstick|cucumber|mushroom|corn|lettuce|celery|yam|taro|turnip|leek|asparagus|artichoke|raw banana|banana flower',
 'Meat, fish and eggs': 'chicken|lamb|mutton|beef|pork|bacon|ham|sausage|fish|salmon|tuna|sardine|pomfret|basa fish|prawn|shrimp|crab|squid|egg|egg white|egg yolk|quail egg',
 'Dairy and alternatives': 'coconut milk|almond milk|soy milk|milk|buttermilk|condensed milk|milk powder|cream|sour cream|yogurt|paneer|tofu|cheese|mozzarella cheese|cheddar cheese|parmesan cheese|cream cheese|butter|ghee',
 'Grains, pulses and flour': 'rice|brown rice|basmati rice|rice flour|wheat flour|whole wheat flour|gram flour|corn flour|all purpose flour|oat|semolina|millet|quinoa|barley|buckwheat|lentil|chickpea|chana dal|urad dal|moong dal|toor dal|masoor dal|kidney bean|black eyed bean|soybean|pasta|noodle|bread|breadcrumb|vermicelli|poha|sago',
 'Spices': 'coriander seed|cumin|coriander powder|turmeric|black pepper|white pepper|chilli powder|chilli|paprika|garam masala|mustard seed|fennel seed|fenugreek seed|nigella seed|carom seed|cinnamon|cardamom|clove|nutmeg|mace|star anise|asafoetida|saffron|amchur|curry powder|sambar powder|rasam powder|chaat masala',
 'Herbs and aromatics': 'garlic|ginger|curry leaf|bay leaf|coriander leaf|mint|basil|oregano|thyme|rosemary|dill|parsley|lemongrass|fenugreek leaf',
 'Condiments, oils and sweeteners': 'soy sauce|fish sauce|tomato sauce|tomato ketchup|mayonnaise|mustard sauce|vinegar|tamarind|salt|sugar|brown sugar|jaggery|honey|maple syrup|olive oil|coconut oil|sesame oil|sunflower oil|mustard oil|oil|chutney|pickle',
 'Fruit, nuts and seeds': 'lemon|lime|coconut|mango|apple|banana|orange|pineapple|grape|raisin|date|fig|pomegranate|strawberry|blueberry|avocado|papaya|jackfruit|almond|cashew|peanut|walnut|pistachio|sesame seed|poppy seed|flax seed|chia seed|pumpkin seed|sunflower seed',
 'Baking and other': 'baking powder|baking soda|yeast|vanilla|cocoa powder|chocolate|gelatin|agar agar|water|stock'
}
ALIASES = {'brinjal':'eggplant','aubergine':'eggplant','capsicum':'bell pepper','palak':'spinach','bhindi':'okra','curd':'yogurt','yoghurt':'yogurt','besan':'gram flour','maida':'all purpose flour','atta':'whole wheat flour','jeera':'cumin','cumin seed':'cumin','coriander seed':'coriander seed','dhania leaf':'coriander leaf','coriander':'coriander leaf','kasuri methi':'fenugreek leaf','red chilli':'chilli','green chilli':'chilli','cloves garlic':'garlic'}
def clean_name(line):
    text=line.lower().replace('_',' ')
    if re.search(r'\b(?:cotton|thread|toothpick|skewer|foil|parchment|coal|charcoal|equipment)\b',text):
        return ''
    text=re.sub(r'\b(?:as per (?:the experiment|taste|use|requirement)|as much as|according to taste|as needed|as required)\b',' ',text)
    text=re.sub(r'^(?:\s*(?:of|or|and)\s+)+','',text)
    text=re.sub(r'\b(?:leaves|leave)\b','leaf',text)
    text=re.sub(r'\b(?:strawberries|strawberrie)\b','strawberry',text)
    text=re.sub(r'\bblueberries\b','blueberry',text)
    text=re.sub(r'\basafetida\b','asafoetida',text)
    text=re.sub(r'\b(?:chili|chile)\b','chilli',text)
    text=re.sub(r'\b(?:arhar|tur) dal\b','toor dal',text)
    text=re.sub(r'\bkalonji\b','nigella',text)
    text=re.sub(r'\boatmeal\b','oat',text)
    text=re.sub(r'\bnugget curry leaf\b','curry leaf',text)
    text=re.split(r'\s+[-–]\s+|\b(?:for|to taste|as required|as needed)\b',text)[0]
    text=re.sub(r'\([^)]*\)',' ',text)
    text=re.sub(r'[\d¼½¾⅓⅔⅛⅜⅝⅞./+–-]+',' ',text)
    text=re.sub(r'\b(?:to|cups?|tablespoons?|teaspoons?|tbsp|tsp|grams?|kilograms?|g|kg|ml|litres?|liters?|inches?|inch|cm|oz|pounds?|packets?|cans?|bunch|pieces?|large|small|medium|whole|fresh|finely|chopped|grated|sliced|diced|minced|crushed|peeled|boiled|cooked|dried|dry|optional)\b',' ',text)
    text=' '.join(text.split()).strip(' ,;:')
    text=re.sub(r'\bpotatoes\b','potato',text)
    text=re.sub(r'\btomatoes\b','tomato',text)
    text=re.sub(r'\b(?:chilies|chillies)\b','chilli',text)
    text=re.sub(r'\b([a-z]{3,})s\b',lambda m:m[0] if m[0].endswith(('ss','us')) else m[1],text)
    text=re.sub(r'^(?:(?:of|or|and)\s+)+','',text).strip()
    if text in {'as per', 'taste', 'use', 'experiment', 'required', 'needed'}:return ''
    return text

def pantry_groups(lines):
    buckets={k:set() for k in GROUPS}
    names={name:group for group,items in GROUPS.items() for name in items.split('|')}
    candidates=sorted(set(names)|set(ALIASES),key=len,reverse=True)
    for line in lines:
        text=clean_name(line)
        if not text:continue
        match=next((key for key in candidates if re.search(r'\b'+re.escape(key)+r'\b',text)),None)
        if match:
            name=ALIASES.get(match,match)
            buckets[names[name]].add(name)
        else:
            buckets['Baking and other'].add(text)
    return [{'name':name,'ingredients':sorted(items)} for name,items in buckets.items() if items]
