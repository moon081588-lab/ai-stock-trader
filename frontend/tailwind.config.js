/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Dark surfaces, layered so cards read against the page without borders.
        base: "#101014",
        surface: "#17181D",
        raised: "#1D1F26",
        hover: "#23252E",
        line: "#2A2C34",
        // Korean convention: red = up, blue = down.
        up: { DEFAULT: "#F5636E", soft: "#2B1A1E", dim: "#C74A55" },
        down: { DEFAULT: "#5B8DEF", soft: "#161E2E", dim: "#4874C4" },
        brand: "#3182F6",
        ink: { DEFAULT: "#EAEBEF", muted: "#9BA0AB", faint: "#6B7180" },
      },
      fontFamily: {
        sans: [
          "Pretendard",
          "-apple-system",
          "BlinkMacSystemFont",
          "Apple SD Gothic Neo",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: ["SF Mono", "ui-monospace", "Menlo", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "0.875rem" }],
      },
      borderRadius: { xl2: "1.125rem" },
      keyframes: {
        flashUp: { "0%": { backgroundColor: "rgba(245,99,110,0.18)" }, "100%": {} },
        flashDown: { "0%": { backgroundColor: "rgba(91,141,239,0.18)" }, "100%": {} },
      },
      animation: {
        flashUp: "flashUp 700ms ease-out",
        flashDown: "flashDown 700ms ease-out",
      },
    },
  },
  plugins: [],
};
