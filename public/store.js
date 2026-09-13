export const LIKED_KEY = 'recipe-room:liked:v1';
export const RECENT_KEY = 'recipe-room:recent:v1';
export function isRecipe(value) {
  return value && typeof value.key === 'string' && typeof value.title === 'string'
    && Array.isArray(value.ingredients) && value.ingredients.every(x => typeof x === 'string')
    && Array.isArray(value.directions) && value.directions.every(x => typeof x === 'string');
}
export function readRecipes(storage, key) {
  try {
    const value = JSON.parse(storage.getItem(key) || '[]');
    return Array.isArray(value) ? value.filter(isRecipe) : [];
  } catch { return []; }
}
export function signature(recipe) {
  return JSON.stringify([recipe.title, recipe.ingredients, recipe.directions]);
}
export function toggleLiked(recipes, recipe, storage) {
  const exists = recipes.some(item => signature(item) === signature(recipe));
  const next = exists ? recipes.filter(item => signature(item) !== signature(recipe)) : [recipe, ...recipes];
  // Persist before changing the UI: failed writes must never report success.
  storage.setItem(LIKED_KEY, JSON.stringify(next));
  return {recipes: next, liked: !exists};
}
