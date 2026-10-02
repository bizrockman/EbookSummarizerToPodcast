import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        mist: "#e2e8f0",
        mint: "#10b981",
        coral: "#f97316",
        sky: "#0ea5e9"
      },
      boxShadow: {
        panel: "0 12px 40px rgba(15, 23, 42, 0.16)"
      }
    }
  },
  plugins: []
};

export default config;
