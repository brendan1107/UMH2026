import { initializeApp, getApps, getApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
    apiKey: "AIzaSyAm80QHqxPx5WkMheOxlm3ORWy2AlE6IvQ",
    authDomain: "fb-genie.firebaseapp.com",
    projectId: "fb-genie",
    storageBucket: "fb-genie.appspot.com",
    messagingSenderId: "38109183345",
    appId: "1:38109183345:web:0b1de42463e450cda7cad0",
};

// Prevent multiple initialization
const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();

// ✅ THESE ARE THE IMPORTANT EXPORTS
export const auth = getAuth(app);
export const db = getFirestore(app);