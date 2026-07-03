import type { Config } from "tailwindcss";

// NOTE: This is the Step 1 structural placeholder only.
// Dark-mode NOC color tokens (severity colors: green/orange/red/black,
// per the brief) and the shadcn/ui theme extension are defined in the
// Dashboard step (Step 7), not here — adding them now without the
// components that consume them would just be dead config.
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
} satisfies Config;
