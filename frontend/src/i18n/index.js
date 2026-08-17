import { useEffect, useState } from "react";
import es from "./es.json";
import en from "./en.json";
import pt from "./pt.json";
import de from "./de.json";
import ja from "./ja.json";

const catalogs = { es, en, pt, de, ja };
export const supportedLanguages = ["es", "en", "pt", "de", "ja"];

function getStoredLanguage() {
  const saved = localStorage.getItem("language") || "es";
  return catalogs[saved] ? saved : "es";
}

export function useI18n() {
  const [lang, setLangState] = useState(getStoredLanguage);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = "ltr";
  }, [lang]);

  useEffect(() => {
    const handler = () => setLangState(getStoredLanguage());
    window.addEventListener("tyakxa-language-change", handler);
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener("tyakxa-language-change", handler);
      window.removeEventListener("storage", handler);
    };
  }, []);

  const catalog = catalogs[lang] || catalogs.es;
  const t = (key, fallback = key) => {
    const value = key.split(".").reduce((acc, part) => acc?.[part], catalog);
    if (value) return value;
    const baseValue = key.split(".").reduce((acc, part) => acc?.[part], catalogs.es);
    return baseValue || fallback;
  };
  const setLanguage = (nextLang) => {
    const safeLang = catalogs[nextLang] ? nextLang : "es";
    localStorage.setItem("language", safeLang);
    setLangState(safeLang);
    window.dispatchEvent(new CustomEvent("tyakxa-language-change", { detail: { lang: safeLang } }));
  };
  return { lang, t, setLanguage, supportedLanguages };
}

export { catalogs };
