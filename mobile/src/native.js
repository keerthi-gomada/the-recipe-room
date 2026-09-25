import { Capacitor } from '@capacitor/core';
import { App } from '@capacitor/app';
if(Capacitor.isNativePlatform() && Capacitor.getPlatform()==='android'){
  App.addListener('backButton',()=>{if(!window.recipeRoomBack?.())App.minimizeApp();});
}
