import type { Config } from "tailwindcss";

// Palette per 04_UIUX.md Section 11 (Visual Language):
// neutral base + one accent for Lost, one distinct accent for Found,
// plus a semantic set for status (success/warning/neutral/danger).
const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        lost: {
          DEFAULT: "#e0563f", // warm terracotta — lost items
          light: "#fbe4de",
          dark: "#b8402c",
        },
        found: {
          DEFAULT: "#1f8a70", // teal-green — found items
          light: "#d9f2ea",
          dark: "#146854",
        },
        status: {
          success: "#1f8a4c",
          warning: "#c8862a",
          neutral: "#64748b",
          danger: "#c23b3b",
        },
      },
      spacing: {
        "4.5": "1.125rem",
      },
    },
  },
  plugins: [],
};

export default config;
