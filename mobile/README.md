# The Recipe Room for Android and iOS

Capacitor projects bundle the Recipe Room interface and call the Render backend at `https://reciperoom-backend.onrender.com`. They include separate recipe pages, the ingredients guide, and full recipes saved in device-local Liked storage. Android's back button returns from recipe pages before minimizing the app.

## Prepare

Install Node.js 22 or newer. From this directory:

```powershell
npm ci
npm run sync
npm run check
```

The UI snapshot is in `src/`. To update it from the website, copy `index.html`, `app.css`, `app.js`, `store.js`, `speech.js`, `recommendations.js`, `icon-192.png` and `icon-512.png` from `../frontend/` into `src/`, keeping `src/native.js`, then run `npm run sync`.

## Android

Install Android Studio and its SDK using the [Capacitor environment setup](https://capacitorjs.com/docs/getting-started/environment-setup). Run `npm run android`, let Gradle sync, and select an emulator or USB-connected phone to run the app. Use Android Studio's signed bundle/APK workflow for distribution and keep the signing key private.

## iOS

On a Mac with Xcode installed, run the prepare commands and `npm run ios`. Select your signing team in Xcode, then run on a simulator or connected iPhone. Archive in Xcode for TestFlight/App Store distribution. Windows cannot compile the iOS project.

The current application ID is `com.keerthigomada.thereciperoom`. Confirm it before first publication. Generated native projects are present, but APK/IPA compilation and physical-device testing have not been performed in this Windows workspace, which has no native SDK installed.

## Backend and saved data

Render must expose `POST /api/generate`, `GET /api/ingredients`, and `GET /api/search`. An older deployment with only search will not support generation. API failures show a readable message. Update the API URL in `scripts/build.mjs` if the service changes, then sync.

Likes stay on this device and are separate from browser likes. Uninstalling or clearing application data removes them. Generation and collection search require internet access; saved recipe contents are bundled into local storage for offline reading.


