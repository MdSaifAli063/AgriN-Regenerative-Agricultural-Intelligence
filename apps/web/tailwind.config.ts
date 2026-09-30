import type { Config } from "tailwindcss";
import tailwindAnimate from "tailwindcss-animate";
import typography from "@tailwindcss/typography";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: {
        "2xl": "1280px",
      },
    },
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--text)",
        "surface-soft": "var(--surface-soft)",
        border: "var(--border)",
        text: {
          DEFAULT: "var(--text)",
          muted: "var(--text-muted)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          dark: "var(--primary-dark)",
          deep: "var(--primary-deep)",
          light: "var(--primary-light)",
          foreground: "#FFFFFF",
        },
        // Semantic status colors (non-brand accents)
        status: {
          healthy: "var(--status-healthy)",
          watch: "var(--status-watch)",
          risk: "var(--status-risk)",
          info: "var(--status-info)",
        },
        // NDVI & Environmental Ramp
        ndvi: {
          0: "#DC2626", // -0.2 to 0.1 (bare soil / severe stress)
          20: "#F59E0B", // 0.1 to 0.25 (sparse veg / watch)
          40: "#FDE047", // 0.25 to 0.4 (low vigour)
          60: "#86EFAC", // 0.4 to 0.6 (moderate vigour)
          80: "#16A34A", // 0.6 to 0.75 (dense healthy)
          100: "#14532D", // > 0.75 (exceptional canopy)
        },
      },
      borderRadius: {
        card: "16px",
        btn: "12px",
        pill: "9999px",
        lg: "16px",
        md: "12px",
        sm: "8px",
      },
      boxShadow: {
        card: "0 2px 8px -1px rgba(22, 163, 74, 0.06), 0 1px 3px -1px rgba(22, 163, 74, 0.04)",
        "card-hover": "0 8px 24px -4px rgba(22, 163, 74, 0.12), 0 2px 6px -1px rgba(22, 163, 74, 0.06)",
        "green-sm": "0 1px 2px 0 rgba(22, 163, 74, 0.15)",
        "green-md": "0 4px 12px 0 rgba(22, 163, 74, 0.20)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Noto Sans", "system-ui", "sans-serif"],
        devanagari: ["var(--font-noto-devanagari)", "Noto Sans", "sans-serif"],
        arabic: ["var(--font-noto-arabic)", "Noto Sans", "sans-serif"],
      },
      keyframes: {
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        pulseGreen: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.7", transform: "scale(1.05)" },
        },
      },
      animation: {
        shimmer: "shimmer 1.8s infinite",
        "pulse-green": "pulseGreen 2s ease-in-out infinite",
      },
    },
  },
  plugins: [tailwindAnimate, typography],
};

export default config;
