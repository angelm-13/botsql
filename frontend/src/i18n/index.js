import { useEffect, useState } from "react";
import canonicalEs from "./locales/es.json";
import canonicalEn from "./locales/en.json";
import canonicalPt from "./locales/pt.json";
import canonicalDe from "./locales/de.json";
import canonicalJa from "./locales/ja.json";
import canonicalZhHans from "./locales/zh-Hans.json";
import canonicalZhHant from "./locales/zh-Hant.json";
import canonicalNah from "./locales/nah.json";

const catalogs = {
  es: canonicalEs,
  en: canonicalEn,
  pt: canonicalPt,
  de: canonicalDe,
  ja: canonicalJa,
  "zh-Hans": canonicalZhHans,
  "zh-Hant": canonicalZhHant,
  nah: canonicalNah,
};
export const languageOptions = [
  { code: "es", label: "Español" },
  { code: "en", label: "English" },
  { code: "pt", label: "Português" },
  { code: "de", label: "Deutsch" },
  { code: "ja", label: "日本語" },
  { code: "zh-Hans", label: "简体中文" },
  { code: "zh-Hant", label: "繁體中文" },
  { code: "nah", label: "Nāhuatl" },
];
export const supportedLanguages = languageOptions.map(({ code }) => code);

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
