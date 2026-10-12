import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        mint: { 50: "#ecfdf5", 500: "#10b981", 600: "#059669", 700: "#047857" },
        ink: "#0b1220",
      },
    },
  },
  plugins: [],
};

export default config;
