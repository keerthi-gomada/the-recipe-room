import test from 'node:test';
import assert from 'node:assert/strict';
import { LIKED_KEY, readRecipes, toggleLiked } from '../frontend/store.js';
const recipe={key:'r-test',title:'Paneer',ingredients:['200 g paneer'],directions:['Cook until hot.']};
function memory(){const values=new Map();return {getItem:key=>values.get(key)||null,setItem:(key,value)=>values.set(key,value)};}
test('a liked dish persists with its complete cooking instructions',()=>{const storage=memory();const result=toggleLiked([],recipe,storage);assert.equal(result.liked,true);assert.deepEqual(readRecipes(storage,LIKED_KEY),[recipe]);});
test('unliking removes only that dish',()=>{const storage=memory();const other={...recipe,key:'other',title:'Rice'};const result=toggleLiked([recipe,other],recipe,storage);assert.equal(result.liked,false);assert.deepEqual(readRecipes(storage,LIKED_KEY),[other]);});
test('same dish generated with a different key is not duplicated',()=>{const storage=memory();const result=toggleLiked([recipe],{...recipe,key:'new'},storage);assert.equal(result.liked,false);assert.equal(result.recipes.length,0);});
test('storage failure cannot falsely report a successful like',()=>{const original=[recipe];assert.throws(()=>toggleLiked(original,{...recipe,title:'Rice'},{setItem(){throw Error('QuotaExceededError');}}));assert.deepEqual(original,[recipe]);});
test('malformed saved data does not crash the app',()=>{assert.deepEqual(readRecipes({getItem:()=>'{broken'},LIKED_KEY),[]);assert.deepEqual(readRecipes({getItem:()=>'{"not":"an array"}'},LIKED_KEY),[]);});
test('unavailable storage and invalid records are handled',()=>{assert.deepEqual(readRecipes({getItem(){throw Error('Disabled');}},LIKED_KEY),[]);assert.deepEqual(readRecipes({getItem:()=>JSON.stringify([recipe,{title:'missing instructions'}])},LIKED_KEY),[recipe]);});
