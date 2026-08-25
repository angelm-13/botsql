import React from "react";
import PropTypes from "prop-types";
import { languageOptions, useI18n } from "../i18n";

export default function LanguagePicker({ className = "" }) {
  const { lang, t, setLanguage } = useI18n();

  return (
    <label className={`language-picker ${className}`.trim()}>
      {t("common.language", "Idioma")}
      <select value={lang} onChange={(event) => setLanguage(event.target.value)}>
        {languageOptions.map(({ code, label }) => (
          <option key={code} value={code}>{label}</option>
        ))}
      </select>
    </label>
  );
}

LanguagePicker.propTypes = {
  className: PropTypes.string,
};
