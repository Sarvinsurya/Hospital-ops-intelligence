/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Haulix-style control-room dark palette
        ink: {
          900: "#0b0c0f",   // deepest background
          800: "#0e0f13",   // app canvas
          700: "#14161c",   // panel
          600: "#1a1d25",   // card
          500: "#232732",   // raised
          400: "#2d323f",   // border
        },
        lime: {
          DEFAULT: "#d4f23a", // primary neon accent
          soft: "#c3e22e",
          dim: "#8a9e1f",
        },
        status: {
          critical: "#ff5c5c",
          warning: "#ffb545",
          normal: "#43d9a3",
          info: "#5ca8ff",
        },
        muted: "#8b92a3",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        xl2: "1.25rem",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(212,242,58,0.15), 0 8px 30px rgba(0,0,0,0.5)",
        card: "0 4px 24px rgba(0,0,0,0.4)",
      },
      backgroundImage: {
        "grid-faint":
          "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};
