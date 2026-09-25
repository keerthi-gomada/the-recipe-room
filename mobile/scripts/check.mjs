import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const html=fs.readFileSync('www/index.html','utf8');
for(const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g))new vm.Script(match[1]);
assert(html.includes('window.RECIPE_NATIVE=true'));
assert(html.includes('https://reciperoom-backend.onrender.com'));
assert(!html.includes('cdn.tailwindcss.com'));
assert(!html.includes('unpkg.com'));
assert(!html.includes('fonts.googleapis.com'));
for(const name of ['app.css','app.js','store.js','speech.js','native.js','icon-192.png','icon-512.png'])assert(fs.statSync('www/'+name).size>0);
const config=JSON.parse(fs.readFileSync('capacitor.config.json','utf8'));
assert(!config.server.url,'UI must be bundled, not a remote website.');
console.log('Mobile assets, API configuration and native shell checks passed.');

