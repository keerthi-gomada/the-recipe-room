const fractions = {'¼':.25,'½':.5,'¾':.75,'⅓':1/3,'⅔':2/3,'⅛':.125,'⅜':.375,'⅝':.625,'⅞':.875};
const number = '(?:\\d+\\s+\\d+\\s*/\\s*\\d+|\\d+\\s*/\\s*\\d+|\\d*[¼½¾⅓⅔⅛⅜⅝⅞]|(?:\\d*\\.)?\\d+)';
const amount = `(${number})(?:\\s*(–|—|-|to)\\s*(${number}))?`;
const units = '(?:kilograms?|kg|grams?|g|millilitres?|milliliters?|ml|litres?|liters?|l|cups?|tablespoons?|teaspoons?|tbsp|tsp|cloves?|sprigs?|tomatoes|tomato|onions?|eggs?|chillies)';
function value(text) {
  text=text.trim().replace(/\s*\/\s*/g,'/');
  const last=text.slice(-1);
  if(fractions[last]) return Number(text.slice(0,-1)||0)+fractions[last];
  return text.split(/\s+/).reduce((sum,part)=>sum+(part.includes('/')?part.split('/').map(Number).reduce((a,b)=>a/b):Number(part)),0);
}
function rounded(n, metric, count) {
  if(n===0) return '0';
  if(metric) return String(n>=1?Math.round(n):Math.max(.1,Math.round(n*10)/10));
  if(count) return String(Math.max(.5,Math.round(n*2)/2));
  // Keep tiny seasonings measurable, then use half-unit increments.
  if(n<=.25) return n<=.1875?'1/8':'1/4';
  return String(Math.max(.5,Math.round(n*2)/2));
}
function measurement(a,sep,b,unit,factor) {
  let outputUnit=unit;
  if(/^(?:kg|kilograms?)$/i.test(unit)){factor*=1000;outputUnit='g';}
  if(/^(?:l|litres?|liters?)$/i.test(unit)){factor*=1000;outputUnit='ml';}
  const metric=/^(?:grams?|g|millilitres?|milliliters?|ml)$/i.test(outputUnit);
  const count=!metric && !/^(?:cups?|tablespoons?|teaspoons?|tbsp|tsp)$/i.test(outputUnit);
  let first=rounded(value(a)*factor,metric,count);
  let last=b?rounded(value(b)*factor,metric,count):null;
  if(metric && Math.max(Number(first), Number(last || first))>=1000){
    outputUnit=/^(?:g|grams?)$/i.test(outputUnit)?'kg':'L';
    first=String(Number(first)/1000);
    if(last!==null)last=String(Number(last)/1000);
  }
  return first+(last&&last!==first?` ${sep} ${last}`:'')+(outputUnit?` ${outputUnit}`:'');
}
export function scaleRecipe(recipe, people, base) {
  if(!Number.isFinite(base)||base<=0||!Number.isInteger(people)||people<1||people>7) return recipe;
  const factor=people/base;
  const generated=recipe.source==='generated'||recipe.is_generated===true;
  const measured=new RegExp(`(^|[^\\w./])${amount}\\s*(${units})\\b`,'gi');
  const leading=new RegExp(`^(\\s*)${amount}\\s*(${units}\\b)?(?=\\s|$|[A-Za-z])`,'i');
  const inText=line=>line.replace(measured,(_,prefix,a,sep,b,unit)=>prefix+measurement(a,sep,b,unit,factor));
  return {...recipe,servings:people,
    ingredients:recipe.ingredients.map(line=>{
      if(generated) line=line.replace(/small onion \(80 g\)/i,'small onion (about 80 g each)');
      const match=leading.exec(line);
      if(!match) return inText(line);
      const [,space,a,sep,b,unit]=match;
      const tail=line.slice(match[0].length);
      // Do not scale package sizes or preparation dimensions in the remaining text.
      return space+measurement(a,sep,b,unit||'',factor)+(tail&&!/^\s/.test(tail)?' ':'')+tail;
    }),
    directions:recipe.directions.map(line=>inText(generated?line.replace(/its teaspoon of oil/gi,'its measured oil'):line)
      .replace(/\bserves\s+\d+\b/gi,`serves ${people}`)
      .replace(/\bbetween (?:two|\d+) (plates|bowls)\b/gi,`among ${people} $1`))};
}


