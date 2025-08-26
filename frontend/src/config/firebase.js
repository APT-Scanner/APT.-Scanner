// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyBPn1nLc4EayVO6nkwEu3TagYB_aaCRamU",
  authDomain: "apt-scanner-7b124.firebaseapp.com",
  projectId: "apt-scanner-7b124",
  storageBucket: "apt-scanner-7b124.firebasestorage.app",
  messagingSenderId: "948013554379",
  appId: "1:948013554379:web:101e5c56dea883b39ed94e",
  measurementId: "G-8R8P8HRVBK"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export { app, auth };