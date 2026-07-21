import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: "#0B2545",
          blue: "#1B6EC2",
          amber: "#E8871E",
        },
      },
    },
  },
  plugins: [],
};

export default config;
