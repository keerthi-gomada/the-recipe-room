import { LIKED_KEY, RECENT_KEY, readRecipes, signature, toggleLiked } from './store.js';

const API_BASE = window.RECIPE_API_BASE || '';
const $ = id => document.getElementById(id);
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
const strings = value => (Array.isArray(value) ? value : typeof value === 'string' ? [value] : []).map(String);
let likes = readRecipes({getItem: key => localStorage.getItem(key)}, LIKED_KEY);
let recent = readRecipes({getItem: key => sessionStorage.getItem(key)}, RECENT_KEY);
let results = readRecipes({getItem: key => sessionStorage.getItem(key)}, 'recipe-room:results:v1');
let currentPage = '';
let loading = false;
let guideLoaded = false;
let toastTimer;
let originPage = '#/';
const isLiked = recipe => likes.some(item => signature(item) === signature(recipe));
const findRecipe = key => likes.find(r => r.key === key) || recent.find(r => r.key === key);
const icon = name => `<svg class="icon" aria-hidden="true"><use href="#${name}"/></svg>`;

function announce(message) {
  $('toast').textContent = message;
  $('toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 4000);
}
function likeButton(recipe, withLabel = false) {
  const liked = isLiked(recipe);
  return `<button class="like-button" data-like="${escapeHtml(recipe.key)}" aria-pressed="${liked}" aria-label="${liked ? 'Unlike' : 'Like'} ${escapeHtml(recipe.title)}">${icon('heart')}${withLabel ? `<span>${liked ? 'Liked' : 'Like dish'}</span>` : ''}</button>`;
}
function duration(recipe) {
  const n = Number(recipe.prep_time);
  return Number.isFinite(n) && n > 0 ? `${Math.round(n)} min` : '';
}
function card(recipe) {
  const meta = [duration(recipe), recipe.servings ? `${recipe.servings} servings` : ''].filter(Boolean).join(' · ');
  return `<article class="recipe-card"><a class="card-link" href="#/recipe/${encodeURIComponent(recipe.key)}"><p class="card-label">${escapeHtml(recipe.cuisine || 'Recipe')}</p><h3>${escapeHtml(recipe.title)}</h3><p class="card-meta">${escapeHtml(meta)} <span aria-hidden="true">↗</span></p></a>${likeButton(recipe)}</article>`;
}
function renderCollections() {
  $('resultsGrid').innerHTML = results.map(card).join('');
  $('resultsHeading').hidden = !results.length;
  $('resultsCount').textContent = `${results.length} ${results.length === 1 ? 'dish' : 'dishes'}`;
  $('likedGrid').innerHTML = likes.map(card).join('');
  $('likedEmpty').hidden = likes.length > 0;
  $('likedCount').textContent = likes.length;
  $('likedCount').hidden = !likes.length;
}
function showRecipe(recipe) {
  if (!recipe) {
    $('recipePage').innerHTML = '<div class="empty-state"><h1>Recipe not found.</h1><p>This dish is no longer available on this device.</p><a class="primary-button" href="#/">Explore recipes</a></div>';
    return;
  }
  $('recipePage').innerHTML = `<div class="page-heading"><a class="back-link" href="${originPage}">${icon('arrow')}${originPage === '#/liked' ? 'Liked dishes' : 'All dishes'}</a><p class="card-label">${escapeHtml(recipe.cuisine || 'Recipe')}</p><h1 class="detail-title">${escapeHtml(recipe.title)}</h1></div>
    <div class="detail-toolbar"><div class="detail-meta">${[duration(recipe),recipe.servings ? `${recipe.servings} servings` : '',recipe.diet].filter(Boolean).map(text=>`<span>${escapeHtml(text)}</span>`).join('')}</div>${likeButton(recipe,true)}</div>
    <div class="recipe-content"><section><h2>Ingredients</h2><ul class="ingredients">${recipe.ingredients.map(text=>`<li>${escapeHtml(text)}</li>`).join('')}</ul></section><section><h2>Let’s cook</h2><ol class="directions">${recipe.directions.map(text=>`<li><p>${escapeHtml(text)}</p></li>`).join('')}</ol></section></div>`;
}
function route() {
  const hash = location.hash || '#/';
  const page = hash.startsWith('#/recipe/') ? 'recipe' : hash === '#/liked' ? 'liked' : 'home';
  if (page === 'recipe' && currentPage !== 'recipe') originPage = currentPage === 'liked' ? '#/liked' : '#/';
  for (const name of ['home','liked','recipe']) $(name+'Page').hidden = name !== page;
  $('likedNav').toggleAttribute('aria-current', page === 'liked');
  if (page === 'liked') $('likedNav').setAttribute('aria-current', 'page');
  if (page === 'recipe') {
    let key;
    try { key = decodeURIComponent(hash.slice('#/recipe/'.length)); } catch { key = ''; }
    const recipe = findRecipe(key);
    showRecipe(recipe);
    document.title = recipe ? `${recipe.title} · The Recipe Room` : 'Recipe not found · The Recipe Room';
  } else document.title = page === 'liked' ? 'Liked · The Recipe Room' : 'The Recipe Room';
  currentPage = page;
  window.scrollTo(0,0);
  $('main').focus({preventScroll:true});
}
function normalizeRecipe(dish) {
  const recipe = {title:String(dish.title || 'Untitled recipe'),ingredients:strings(dish.ingredients),directions:strings(dish.directions),cuisine:String(dish.cuisine || ''),prep_time:Number(dish.prep_time)||0,servings:Number(dish.servings)||0,diet:String(dish.diet||'')};
  const existing = [...likes,...recent].find(r=>signature(r)===signature(recipe));
  return {...recipe, key: existing?.key || `r-${typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : Array.from(crypto.getRandomValues(new Uint8Array(16)), n=>n.toString(16).padStart(2,'0')).join('')}`};
}
async function requestRecipes(generated) {
  if (loading) return;
  const query = $('query').value.trim();
  if (!query) { $('query').focus(); $('requestStatus').textContent = 'Add an ingredient to start.'; return; }
  loading = true;
  $('generateButton').disabled = $('searchButton').disabled = true;
  $('recipeForm').setAttribute('aria-busy','true');
  $('requestStatus').textContent = generated ? 'Finding your next favourite…' : 'Searching the collection…';
  try {
    const response = await fetch(generated ? `${API_BASE}/api/generate` : `${API_BASE}/api/search?q=${encodeURIComponent(query)}&include_generated=false`, {
      ...(generated ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({q:query})} : {}),
      signal: AbortSignal.timeout(60000)
    });
    const data = await response.json().catch(()=>({}));
    if (!response.ok || data.error) throw new Error(response.status===404 ? 'Recipe generation is unavailable. The backend needs to be updated.' : typeof data.detail==='string' ? data.detail : data.error || 'Couldn’t load recipes. Please try again.');
    results = (Array.isArray(data.recipes) ? data.recipes : []).map(normalizeRecipe);
    const keys = new Set(results.map(r=>r.key));
    recent = [...results,...recent.filter(r=>!keys.has(r.key))].slice(0,100);
    try { sessionStorage.setItem(RECENT_KEY, JSON.stringify(recent)); sessionStorage.setItem('recipe-room:results:v1', JSON.stringify(results)); } catch { /* Still usable in this session; liked recipes persist separately. */ }
    renderCollections();
    $('requestStatus').textContent = results.length ? '' : 'No dishes found. Try another combination.';
  } catch (error) {
    $('requestStatus').textContent = !navigator.onLine ? 'You’re offline. Your liked dishes are still available.' : error.name==='TimeoutError' ? 'The kitchen is taking longer than usual. Try again shortly.' : error.message;
  } finally {
    loading = false;
    $('generateButton').disabled = $('searchButton').disabled = false;
    $('recipeForm').removeAttribute('aria-busy');
  }
}
async function loadGuide() {
  if (guideLoaded) return;
  $('guideContent').textContent = 'Loading pantry…';
  $('retryGuide').hidden = true;
  try {
    const response = await fetch(`${API_BASE}/api/ingredients`, {signal:AbortSignal.timeout(30000)});
    const data = await response.json();
    if (!response.ok || !Array.isArray(data.ingredients) || !Array.isArray(data.cuisines)) throw new Error();
    $('guideContent').innerHTML = [['Main ingredients',data.ingredients],['Extras',data.additional_ingredients || []],['Cuisines',data.cuisines]].map(([title,items])=>`<section class="guide-group"><h3>${title}</h3><div class="guide-tags">${strings(items).map(text=>`<span>${escapeHtml(text)}</span>`).join('')}</div></section>`).join('');
    guideLoaded = true;
  } catch {
    $('guideContent').textContent = 'The pantry guide is unavailable. Reconnect or check that the backend is up to date.';
    $('retryGuide').hidden = false;
  }
}
$('recipeForm').addEventListener('submit',event=>{event.preventDefault();$('query').blur();requestRecipes(true);});
$('searchButton').addEventListener('click',()=>requestRecipes(false));
$('query').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();$('recipeForm').requestSubmit();}});
document.querySelectorAll('[data-query]').forEach(button=>button.addEventListener('click',()=>{$('query').value=button.dataset.query;requestRecipes(true);}));
document.addEventListener('click',event=>{
  const button = event.target.closest('[data-like]');
  if (!button) return;
  const recipe = findRecipe(button.dataset.like);
  if (!recipe) return;
  try {
    // Re-read persisted likes to preserve updates made in another tab.
    const saved = toggleLiked(readRecipes(localStorage, LIKED_KEY), recipe, localStorage);
    likes = saved.recipes;
    renderCollections();
    if (currentPage==='recipe') showRecipe(recipe);
    const replacement = document.querySelector(`#${currentPage==='recipe'?'recipePage':currentPage==='liked'?'likedGrid':'resultsGrid'} [data-like="${CSS.escape(recipe.key)}"]`);
    if (replacement) replacement.focus({preventScroll:true});
    else $('main').focus({preventScroll:true});
    announce(saved.liked ? 'Saved to Liked.' : 'Removed from Liked.');
  } catch { announce('Couldn’t save this dish. Device storage may be full or disabled.'); }
});
$('guideButton').addEventListener('click',()=>{$('guide').showModal();loadGuide();});
$('closeGuide').addEventListener('click',()=>$('guide').close());
$('retryGuide').addEventListener('click',loadGuide);
$('guide').addEventListener('click',event=>{if(event.target===$('guide')){const r=$('guide').getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)$('guide').close();}});
document.querySelector('.skip-link').addEventListener('click',event=>{event.preventDefault();$('main').focus();});
window.addEventListener('hashchange',route);
window.addEventListener('storage',event=>{if(event.key===LIKED_KEY){likes=readRecipes(localStorage,LIKED_KEY);renderCollections();if(currentPage==='recipe'){let key=location.hash.slice(9);try{key=decodeURIComponent(key);}catch{}showRecipe(findRecipe(key));}}});
window.recipeRoomBack = () => {if($('guide').open){$('guide').close();return true;}if(currentPage!=='home'){location.hash=originPage==='#/liked'&&currentPage==='recipe'?'#/liked':'#/';return true;}return false;};
let installPrompt;
const standalone = matchMedia('(display-mode: standalone)');
const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
function updateInstall() { $('installButton').hidden=Boolean(window.RECIPE_NATIVE)||standalone.matches||navigator.standalone===true||(!isIOS&&!installPrompt); }
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event;updateInstall();});
window.addEventListener('appinstalled',()=>{$('installButton').hidden=true;$('installHint').hidden=true;});
standalone.addEventListener('change',updateInstall);
$('installButton').addEventListener('click',async()=>{
  if(isIOS){$('installHint').textContent='Open Share → Add to Home Screen → Add. Use Safari if the option is missing.';$('installHint').hidden=false;return;}
  if(installPrompt){try{await installPrompt.prompt();}finally{installPrompt=null;updateInstall();}}
});
updateInstall();
renderCollections();
route();
if(!window.RECIPE_NATIVE && 'serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(()=>{});
