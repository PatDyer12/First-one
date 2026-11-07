// Firebase web config for the sweat-board project (Project settings → Your apps).
// These values are safe to publish: your Firestore rules decide who can read or write.
window.SWEAT_FIREBASE = {
  apiKey: "AIzaSyAzL3ewqWolkJqgdiuk_foONRDQV4AQWcw",
  authDomain: "sweat-board.firebaseapp.com",
  projectId: "sweat-board",
  storageBucket: "sweat-board.firebasestorage.app",
  messagingSenderId: "192999019838",
  appId: "1:192999019838:web:96f51bded21a133940c86f",
};

// reCAPTCHA site key for App Check (Firebase requires it for the slip reader). Site keys are public by design.
// Registered in Firebase under App Check → Apps → Fraud Defense (reCAPTCHA Enterprise), so the Enterprise provider is used
window.SWEAT_RECAPTCHA = "6Le_MxUuAAAAAK6OZ6OlGH8JY-3VjYZtPjlEow-D";
window.SWEAT_RECAPTCHA_ENT = true;
