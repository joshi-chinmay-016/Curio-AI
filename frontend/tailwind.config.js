/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
    "./services/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        border: "hsl(var(--border))",
        primary: "hsl(var(--primary))",
        accent: "hsl(var(--accent))",
        success: "hsl(var(--success))",
        warning: "hsl(var(--warning))",
        danger: "hsl(var(--danger))",

        // Curio Gap Report Isometric Editorial Palette
        ice: "#E8EEF3",
        navy: "#0F2B4A",
        cobalt: "#3A63FF",
        "gap-orange": "#FF6B1A",
        fog: "#C4CDD6",
        chalk: "#FFFFFF",
      },
      fontFamily: {
        sora: ["var(--font-sora)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
        "ibm-plex-mono": ["var(--font-mono)", "monospace"],
        sans: ["var(--font-dm-sans)", "sans-serif"],
        heading: ["var(--font-sora)", "sans-serif"],
        body: ["var(--font-dm-sans)", "sans-serif"],
      },
      boxShadow: {
        keycap: "0 4px 0 0 #0F2B4A, 0 6px 12px rgba(15,43,74,0.1)",
        "keycap-pressed": "0 0px 0 0 #0F2B4A",
        "keycap-gap": "0 4px 0 0 #FF6B1A, 0 6px 12px rgba(255,107,26,0.15)",
        "keycap-cobalt": "0 4px 0 0 #3A63FF, 0 6px 12px rgba(58,99,255,0.15)",
        editorial: "4px 4px 0 0 #0F2B4A",
        "editorial-lg": "8px 8px 0 0 #0F2B4A",
      },
      borderRadius: {
        editorial: "6px",
        keycap: "4px",
        badge: "3px",
      },
    },
  },
  plugins: [],
};

