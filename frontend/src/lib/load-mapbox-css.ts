const MAPBOX_CSS_ID = "mapbox-gl-css";
const MAPBOX_CSS_HREF = "https://api.mapbox.com/mapbox-gl-js/v3.9.3/mapbox-gl.css";

export function loadMapboxCss() {
  if (typeof document === "undefined") return;
  if (document.getElementById(MAPBOX_CSS_ID)) return;

  const link = document.createElement("link");
  link.id = MAPBOX_CSS_ID;
  link.rel = "stylesheet";
  link.href = MAPBOX_CSS_HREF;
  document.head.appendChild(link);
}