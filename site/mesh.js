const languageButtons = [...document.querySelectorAll("[data-language]")];
const localizedNodes = [...document.querySelectorAll("[data-lang]")];

function setLanguage(language) {
  document.documentElement.lang = language;
  localizedNodes.forEach((node) => {
    node.hidden = node.dataset.lang !== language;
  });
  languageButtons.forEach((button) => {
    const active = button.dataset.language === language;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  try {
    localStorage.setItem("digital-field-language", language);
  } catch {
    // The site remains fully usable when local preferences are unavailable.
  }
}

languageButtons.forEach((button) => {
  button.addEventListener("click", () => setLanguage(button.dataset.language));
});

let initialLanguage = "es";
try {
  const stored = localStorage.getItem("digital-field-language");
  if (stored === "en" || stored === "es") initialLanguage = stored;
  else if (navigator.language.toLowerCase().startsWith("en")) initialLanguage = "en";
} catch {
  // Spanish remains the deterministic default.
}
setLanguage(initialLanguage);

fetch("mesh.json")
  .then((response) => response.json())
  .then((mesh) => {
    const label = document.querySelector("[data-status-label]");
    if (label && mesh?.version) label.textContent = `MESH ${mesh.version}`;
  })
  .catch(() => {
    // Static content already contains every essential identity statement.
  });

