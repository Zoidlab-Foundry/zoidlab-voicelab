/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0d0f14", panel: "#141821", panel2: "#1b212d", line: "#28303e",
        cy: "#5eead4", vi: "#2dd4bf", ind: "#14b8a6", prism: "#2dd4bf",
        ink: "#e8eef5", dim: "#93a4b8", faint: "#5f7185",
        ok: "#22c55e", warn: "#f4b860", bad: "#ef4444",
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(45,212,191,0.40)",
      },
    },
  },
  plugins: [],
};
