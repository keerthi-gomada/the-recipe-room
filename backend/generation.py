"""Compose dishes using Epicure-Core flavour vectors and explicit cooking plans.

Embeddings rank compatible seasonings; they do not generate instruction text.
Every accepted input has a measured quantity and a defined cooking step.
"""
from dataclasses import dataclass
import numpy as np

MODEL_ID = 'Kaikaku/epicure-core'

@dataclass(frozen=True)
class Method:
    preparation: str
    cooking: str
    minutes: int
    water: int = 0
    oil: bool = False

# Cook components before combining so roots, leafy greens and proteins do not
# receive the same arbitrary simmer time. Water quantities are per component.
METHODS = {
    'potato': Method('peeled and cut into 1.5 cm cubes', 'Simmer the potato in its measured water over medium heat for 12–15 minutes until a fork slides easily into the cubes. Drain.', 18, 750),
    'cauliflower': Method('cut into small florets', 'Simmer the cauliflower in its measured water over medium heat for 5–7 minutes until just fork-tender. Drain well.', 10, 750),
    'carrot': Method('peeled and sliced 5 mm thick', 'Simmer the carrot in its measured water over medium heat for 8–10 minutes until fork-tender. Drain.', 13, 750),
    'broccoli': Method('cut into small florets', 'Simmer the broccoli in its measured water over medium heat for 3–4 minutes until bright green and just tender. Drain well.', 7, 750),
    'mushroom': Method('wiped clean and sliced', 'Cook the mushroom in its teaspoon of oil over medium-high heat for 8–10 minutes, stirring often, until lightly browned and its released liquid has mostly evaporated.', 11, oil=True),
    'spinach': Method('rinsed, drained and roughly chopped', 'Cook the spinach in its teaspoon of oil over medium heat for 2–3 minutes, stirring until wilted. Let excess liquid evaporate.', 4, oil=True),
    'paneer': Method('cut into 2 cm cubes', 'Warm the paneer in its teaspoon of oil over medium-low heat for 3–4 minutes, turning gently, until hot throughout. Avoid prolonged cooking.', 5, oil=True),
    'tofu': Method('firm tofu, drained, patted dry and cut into 2 cm cubes', 'Cook the tofu in its teaspoon of oil over medium heat for 6–8 minutes, turning gently, until lightly golden and hot throughout.', 9, oil=True),
    'chickpea': Method('canned chickpeas, drained and rinsed; do not use dried chickpeas', 'Simmer the canned chickpea in its measured water over medium-low heat for 5 minutes until hot throughout. Drain. This method is for cooked or canned chickpeas, not dried chickpeas.', 8, 300),
    'bell_pepper': Method('deseeded and cut into 2 cm pieces', 'Cook the bell pepper in its teaspoon of oil over medium-high heat for 5–6 minutes, stirring often, until softened but still slightly crisp.', 7, oil=True),
    'zucchini': Method('cut into 1 cm half-moons', 'Cook the zucchini in its teaspoon of oil over medium-high heat for 5–7 minutes, turning occasionally, until lightly golden and just tender.', 8, oil=True),
    'eggplant': Method('cut into 1.5 cm cubes', 'Cook the eggplant in its teaspoon of oil over medium heat for 3 minutes. Add its measured water, cover and cook over low heat for 10–12 minutes, stirring halfway, until completely soft. Uncover to evaporate any remaining water.', 17, 80, True),
    'pea': Method('shelled fresh or frozen peas', 'Simmer the pea in its measured water over medium heat for 3–5 minutes until tender. Drain.', 8, 300),
    'chicken': Method('boneless chicken, cut into 2 cm pieces; do not rinse raw chicken', 'Cook the chicken in its teaspoon of oil over medium heat for 8–12 minutes, turning frequently. Check the thickest pieces with a food thermometer: they must reach 74°C / 165°F. Continue cooking if needed. Transfer to a clean plate and wash utensils that touched raw chicken.', 15, oil=True),
    'rice': Method('dry basmati rice, rinsed and drained', 'Put the rice and its 300 ml water in a saucepan. Bring to a boil, cover tightly and reduce heat to low. Cook for 12 minutes, then turn off the heat and leave covered for 10 minutes. Fluff with a fork; the grains should be tender with no standing water.', 26, 300),
}

# name: (quantity/preparation, stage). Explicit user seasonings are never dropped.
EXTRAS = {
    'onion': ('1 small onion (80 g), finely chopped', 'onion'),
    'garlic': ('2 garlic cloves, minced', 'aromatic'),
    'ginger': ('2 teaspoons grated ginger', 'aromatic'),
    'tomato': ('150 g tomato, finely chopped', 'tomato'),
    'coconut_milk': ('100 ml coconut milk', 'liquid'),
    'coconut': ('2 tablespoons grated coconut', 'finish'),
    'soy_sauce': ('2 teaspoons soy sauce', 'liquid'),
    'lemon': ('2 teaspoons lemon juice', 'finish'),
    'lime': ('2 teaspoons lime juice', 'finish'),
    'curry_leaf': ('8 curry leaves, rinsed and dried thoroughly', 'temper'),
    'mustard_seed': ('1/2 teaspoon mustard seeds', 'temper'),
    'cumin': ('1/4 teaspoon ground cumin', 'spice'),
    'coriander': ('1/4 teaspoon ground coriander', 'spice'),
    'turmeric': ('1/4 teaspoon ground turmeric', 'spice'),
    'black_pepper': ('1/4 teaspoon ground black pepper', 'spice'),
    'fennel_seed': ('1/4 teaspoon ground fennel seeds', 'spice'),
    'cinnamon': ('1 small pinch ground cinnamon', 'spice'),
    'garam_masala': ('1/4 teaspoon garam masala', 'spice'),
    'paprika': ('1/4 teaspoon paprika', 'spice'),
    'oregano': ('1/2 teaspoon dried oregano', 'spice'),
    'basil': ('1 tablespoon chopped fresh basil', 'finish'),
}

@dataclass(frozen=True)
class Style:
    label: str
    pole: str
    base: str
    essentials: tuple
    seasonings: tuple
    oil: str = 'neutral cooking oil'

SOUTH_ASIAN = 'cuisine:South_Asian'
STYLES = {
    'indian': Style('Indian', SOUTH_ASIAN, 'tomato', ('garlic', 'ginger', 'tomato'), ('cumin', 'coriander', 'turmeric', 'garam_masala')),
    'south indian': Style('South Indian', SOUTH_ASIAN, 'dry', ('mustard_seed', 'curry_leaf', 'coconut'), ('turmeric', 'cumin', 'black_pepper'), 'coconut oil'),
    'north indian': Style('North Indian', SOUTH_ASIAN, 'tomato', ('garlic', 'ginger', 'tomato'), ('garam_masala', 'cumin', 'coriander', 'turmeric')),
    'chettinad': Style('Chettinad', SOUTH_ASIAN, 'dry', ('curry_leaf', 'garlic', 'ginger', 'black_pepper', 'fennel_seed'), ('coriander', 'cumin', 'cinnamon'), 'sesame oil'),
    'bengali': Style('Bengali', SOUTH_ASIAN, 'broth', ('mustard_seed', 'ginger'), ('turmeric', 'cumin', 'coriander')),
    'kerala': Style('Kerala', SOUTH_ASIAN, 'coconut', ('coconut_milk', 'curry_leaf', 'ginger'), ('black_pepper', 'turmeric', 'cumin'), 'coconut oil'),
    'maharashtrian': Style('Maharashtrian', SOUTH_ASIAN, 'dry', ('garlic', 'coconut'), ('cumin', 'coriander', 'turmeric')),
    'andhra': Style('Andhra', SOUTH_ASIAN, 'dry', ('garlic', 'curry_leaf', 'paprika'), ('coriander', 'cumin', 'black_pepper')),
    'rajasthani': Style('Rajasthani', SOUTH_ASIAN, 'tomato', ('ginger', 'tomato', 'paprika'), ('cumin', 'coriander', 'fennel_seed'), 'ghee'),
    'gujarati': Style('Gujarati', SOUTH_ASIAN, 'dry', ('mustard_seed', 'ginger', 'lemon'), ('cumin', 'coriander', 'turmeric')),
    'mughlai': Style('Mughlai', SOUTH_ASIAN, 'cream', ('ginger', 'garlic'), ('garam_masala', 'cinnamon', 'cumin'), 'ghee'),
    'goan': Style('Goan', SOUTH_ASIAN, 'coconut', ('coconut_milk', 'garlic', 'lime', 'paprika'), ('coriander', 'cumin', 'black_pepper'), 'coconut oil'),
    'italian': Style('Italian', 'cuisine:Mediterranean', 'tomato', ('garlic', 'tomato', 'basil'), ('oregano', 'black_pepper'), 'olive oil'),
    'continental': Style('Continental', 'cuisine:Western_Atlantic', 'dry', ('garlic', 'lemon'), ('oregano', 'black_pepper'), 'olive oil'),
    'chinese': Style('Chinese', 'cuisine:East_Asian', 'soy', ('ginger', 'garlic', 'soy_sauce'), ('black_pepper',)),
    'thai': Style('Thai', 'cuisine:Southeast_Asian', 'coconut', ('ginger', 'garlic', 'coconut_milk', 'lime', 'basil'), ('coriander', 'black_pepper')),
    'mexican': Style('Mexican', 'cuisine:Latin_American', 'tomato', ('tomato', 'garlic', 'lime'), ('cumin', 'paprika', 'oregano')),
}
ALIASES = {
    'potatoes': 'potato', 'carrots': 'carrot', 'mushrooms': 'mushroom',
    'chickpeas': 'chickpea', 'basmati rice': 'rice', 'basmati_rice': 'rice',
    'bell peppers': 'bell_pepper', 'capsicum': 'bell_pepper', 'peas': 'pea',
    'aubergine': 'eggplant', 'brinjal': 'eggplant', 'tomatoes': 'tomato',
    'onions': 'onion', 'garlic cloves': 'garlic', 'curry leaves': 'curry_leaf',
    'mustard seeds': 'mustard_seed', 'fennel seeds': 'fennel_seed',
    'chicken breast': 'chicken', 'cumin seeds': 'cumin',
}
CUISINE_ALIASES = {'south asian': 'indian', 'east asian': 'chinese',
                   'southeast asian': 'thai', 'mediterranean': 'italian',
                   'western atlantic': 'continental', 'latin american': 'mexican'}


def normalize(text):
    return ' '.join(text.lower().strip().replace('_', ' ').split())


def parse_query(query, cuisine=None):
    parts = query.split('+')
    if cuisine is not None:
        parts += cuisine.split('+')
    if any(not p.strip() for p in parts):
        raise ValueError('Enter ingredients and cuisines separated by +, without empty parts.')
    ingredients, cuisines, unknown = [], [], []
    for part in parts:
        clean = normalize(part).removeprefix('cuisine:')
        style = CUISINE_ALIASES.get(clean, clean)
        if style in STYLES:
            if style not in cuisines:
                cuisines.append(style)
            continue
        key = ALIASES.get(clean, clean.replace(' ', '_'))
        if key in METHODS or key in EXTRAS:
            if key not in ingredients:
                ingredients.append(key)
        else:
            unknown.append(part.strip())
    if unknown:
        raise ValueError('Unsupported ingredients or cuisines: ' + ', '.join(unknown) + '. Choose from the supported list. No inputs were ignored.')
    if not any(key in METHODS for key in ingredients):
        raise ValueError('Add at least one main ingredient, such as rice, paneer, chicken, potato or tofu.')
    if len(ingredients) > 8:
        raise ValueError('Use up to 8 different ingredients per dish.')
    if len(cuisines) > 3:
        raise ValueError('Use up to 3 cuisines. A separate dish is generated for each cuisine.')
    return ingredients, cuisines or ['indian']


def rank_seasonings(engine, ingredients, style):
    missing = [key.replace('_', ' ') for key in ingredients if key not in engine.vocab]
    if missing:
        raise ValueError('Unavailable in the loaded Epicure-Core vocabulary: ' + ', '.join(missing))
    vector = engine.encode_ingredient_list(ingredients)
    pole = engine.get_pole_vector(style.pole)
    if pole is None:
        raise ValueError('The loaded Epicure-Core model is missing the requested cuisine vector.')
    vector = engine.slerp(vector, pole, theta_deg=25)
    ranked = []
    for spice in style.seasonings:
        spice_vector = engine.get_ingredient_vector(spice)
        if spice_vector is not None:
            ranked.append((float(np.dot(vector, spice_vector)), spice))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    if not ranked:
        raise ValueError('No compatible seasonings are available in the Epicure-Core vocabulary.')
    return [spice for _, spice in ranked[:2]]


def compose_dish(engine, requested, cuisine, index=0):
    style = STYLES[cuisine]
    selected = rank_seasonings(engine, requested, style)
    mains = [key for key in requested if key in METHODS]
    # A keyed ingredient plan prevents duplicate pantry or requested ingredients.
    additions = dict.fromkeys(['onion', *style.essentials,
                              *(key for key in requested if key in EXTRAS), *selected])
    non_rice = [key for key in mains if key != 'rice']
    portion = round((300 if 'rice' in mains else 400) / max(1, len(non_rice)) / 10) * 10
    ingredient_lines = []
    directions = ['Measure and prepare all ingredients as listed. This recipe serves 2. Keep each cooked component covered while preparing the next; combine and serve promptly.']
    total_minutes = 10
    for key in mains:
        method = METHODS[key]
        grams = 150 if key == 'rice' else portion
        name = key.replace('_', ' ')
        ingredient_lines.append(f'{grams} g {name} ({method.preparation})')
        if method.water:
            ingredient_lines.append(f'{method.water} ml water for the {name}')
        if method.oil:
            ingredient_lines.append(f'1 teaspoon {style.oil} for the {name}')
        if key == 'rice':
            intro = ''
        elif method.water and not method.oil:
            intro = f'Bring the {method.water} ml water for the {name} to a boil in a small saucepan. '
        else:
            intro = f'Heat the 1 teaspoon oil for the {name} in a nonstick skillet for 30 seconds. '
        directions.append(intro + method.cooking + ' Set aside, covered.')
        total_minutes += method.minutes
    ingredient_lines += [EXTRAS[key][0] for key in additions]
    ingredient_lines += [f'1 tablespoon {style.oil} for the flavour base',
                         '1/8 teaspoon salt, plus more to taste' if 'soy_sauce' in additions else '1/4 teaspoon salt, plus more to taste']
    stages = {stage: [key.replace('_', ' ') for key in additions if EXTRAS[key][1] == stage]
              for stage in ['temper', 'aromatic', 'spice', 'tomato', 'liquid', 'finish']}
    directions.append(f'For the {style.label}-inspired base, heat 1 tablespoon {style.oil} in a large deep skillet over medium heat for 1 minute.')
    if stages['temper']:
        directions.append('Add the ' + ' and '.join(stages['temper']) + '. Partially cover to contain spluttering and stir for 20–30 seconds until fragrant; do not let them burn.')
    directions.append('Add the chopped onion. Cook over medium heat for 5–7 minutes, stirring often, until softened and lightly golden.')
    if stages['aromatic']:
        directions.append('Reduce to medium-low heat. Add the ' + ' and '.join(stages['aromatic']) + ' and stir for 30–60 seconds until fragrant.')
    if stages['spice']:
        directions.append('Reduce heat to low. Add the measured ' + ', '.join(stages['spice']) + ' and salt. Stir for 20 seconds to bloom the seasonings without burning them.')
    if stages['tomato']:
        directions.append('Add the chopped tomato. Cook over medium-low heat for 8–10 minutes, stirring frequently, until it breaks down into a thick sauce. If it sticks, reduce the heat and add 1 tablespoon of the water reserved for the base.')
        total_minutes += 10
    base_water = {'dry': 30, 'tomato': 60, 'broth': 180, 'coconut': 60, 'cream': 60, 'soy': 30}[style.base]
    ingredient_lines.append(f'{base_water} ml water for the flavour base')
    liquid_names = list(stages['liquid'])
    if style.base == 'cream':
        ingredient_lines.append('60 ml single cream')
        liquid_names.append('single cream')
    liquids = ', '.join(liquid_names + ['the remaining measured water for the base'])
    directions.append(f'Add {liquids}. Bring to a gentle simmer over medium-low heat and cook for 3–4 minutes, stirring. Avoid a rolling boil' + (' so the coconut milk stays smooth.' if 'coconut_milk' in additions else '.'))
    if non_rice:
        directions.append('Fold in the cooked ' + ', '.join(key.replace('_', ' ') for key in non_rice) + '. Toss gently over low heat for 2 minutes until everything is hot and coated in the base.')
    if stages['finish']:
        directions.append('Turn off the heat. Stir in the measured ' + ' and '.join(stages['finish']) + '.')
    if 'rice' in mains:
        if non_rice and style.base in ('broth', 'coconut', 'cream', 'tomato'):
            directions.append('Divide the cooked rice between two bowls and spoon the hot mixture over it. Taste and adjust salt before serving.')
            form = 'Rice Bowls'
        else:
            directions.append('Gently fold in the cooked rice over low heat for 1–2 minutes until coated and hot. Taste and adjust salt, then divide between two plates.')
            form = 'Seasoned Rice'
    else:
        form = {'dry': 'Skillet', 'tomato': 'Tomato Braise', 'broth': 'Light Stew',
                'coconut': 'Coconut Stew', 'cream': 'Creamy Braise', 'soy': 'Ginger-Soy Skillet'}[style.base]
        directions.append('Taste and adjust the salt if needed. Divide between two plates and serve warm.')
    diet = 'Non-vegetarian' if 'chicken' in mains else ('Vegetarian' if 'paneer' in mains or style.oil == 'ghee' or style.base == 'cream' else 'Vegan')
    title_keys = non_rice if 'rice' in mains else mains
    title_mains = ' & '.join(key.replace('_', ' ').title() for key in title_keys[:3])
    if len(title_keys) > 3:
        title_mains += ' Medley'
    return {
        'id': -999 - index, 'title': f'{style.label}-Inspired {title_mains} {form}'.replace('  ', ' '),
        'is_generated': True, 'main_ingredient': mains[0], 'requested_ingredients': requested,
        'servings': 2, 'model': MODEL_ID, 'cuisine_pole': style.pole,
        'generation_method': 'Epicure-Core ingredient centroid and cuisine steering; measured cooking plan',
        'flavour_match_score': None, 'flavour_notes': list(dict.fromkeys(key.replace('_', ' ') for key in [*requested, *selected])),
        'ingredients': ingredient_lines, 'directions': directions,
        'cuisine': style.label + '-inspired', 'prep_time': total_minutes + 20, 'diet': diet,
        'selected_seasonings': selected,
    }


def generate_dishes(engine, query, cuisine=None):
    ingredients, cuisines = parse_query(query, cuisine)
    return [compose_dish(engine, ingredients, style, i) for i, style in enumerate(cuisines)]


def generate_dish(engine, main_ingredient, cuisine=None):
    """Backward-compatible single-result helper; API callers use generate_dishes."""
    return generate_dishes(engine, main_ingredient, cuisine)[0]
