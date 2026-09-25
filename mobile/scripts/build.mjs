import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out=path.join(root,'www');
await fs.mkdir(out,{recursive:true});
const ui=path.join(root,'src');
let html=await fs.readFile(path.join(ui,'index.html'),'utf8');
html=html.replace('<link rel="manifest" href="./manifest.webmanifest">','');
html=html.replace('<script type="module" src="./app.js"></script>', '<script>window.RECIPE_NATIVE=true;window.RECIPE_API_BASE="https://reciperoom-backend.onrender.com";</script>\n  <script src="./native.js" defer></script>\n  <script type="module" src="./app.js"></script>');
await fs.writeFile(path.join(out,'index.html'),html);
for(const name of ['app.css','app.js','store.js','speech.js','recommendations.js','icon-192.png','icon-512.png'])await fs.copyFile(path.join(ui,name),path.join(out,name));
await build({entryPoints:[path.join(ui,'native.js')],outfile:path.join(out,'native.js'),bundle:true,minify:true,format:'iife',target:['safari15','chrome100']});
console.log('Built bundled mobile UI, recipe pages and device-local liked recipes.');


