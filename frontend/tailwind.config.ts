import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Sidebar panel — deep slate-indigo (replaces forest green)
        panel: {
          DEFAULT: '#171a2e',
          light:   '#1e2340',
          mid:     '#252b4a',
          text:    '#c5cee8',
          muted:   '#7a84a8',
          border:  '#2c3255',
        },
        // Canvas — warm paper off-white
        canvas: {
          DEFAULT: '#f9f6f1',
          light:   '#ffffff',
          mid:     '#f0ebe2',
          dark:    '#e8e2d8',
          border:  '#ddd6c8',
        },
        // Ink — warm dark text hierarchy
        ink: {
          DEFAULT: '#1e1b2e',
          mid:     '#42405a',
          light:   '#7a7898',
          faint:   '#aeacbe',
        },
        // Primary — muted indigo accent
        primary: {
          DEFAULT: '#4f5894',
          dark:    '#3a4278',
          light:   '#dde0f8',
          muted:   '#8892c0',
        },
        // Sage — soft teal secondary accent
        sage: {
          DEFAULT: '#5a8a7a',
          dark:    '#3d6358',
          light:   '#c4e0d8',
          muted:   '#7eaaa0',
          bg:      '#eef5f3',
        },
        // Ochre — citation highlights, document context bar
        ochre: {
          DEFAULT: '#b07830',
          dark:    '#8a5c18',
          light:   '#fdf3e0',
          mid:     '#e8c870',
          border:  '#d8b060',
          text:    '#7a4c10',
        },
        // Coral — errors, out-of-scope flags
        coral: {
          DEFAULT: '#c05040',
          light:   '#fdf0ee',
          border:  '#e8a898',
          text:    '#8c2a1a',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
      borderRadius: {
        sm:    '4px',
        DEFAULT: '6px',
        md:    '8px',
        lg:    '10px',
        xl:    '14px',
        '2xl': '18px',
        '3xl': '24px',
      },
      boxShadow: {
        xs:      '0 1px 2px rgba(30,27,46,0.06)',
        sm:      '0 2px 6px rgba(30,27,46,0.08), 0 1px 2px rgba(30,27,46,0.05)',
        md:      '0 4px 16px rgba(30,27,46,0.10), 0 2px 4px rgba(30,27,46,0.07)',
        lg:      '0 8px 32px rgba(30,27,46,0.12), 0 4px 8px rgba(30,27,46,0.08)',
        sidebar: '4px 0 32px rgba(0,0,0,0.24)',
        card:    '0 1px 3px rgba(30,27,46,0.07), 0 2px 8px rgba(30,27,46,0.05)',
      },
      keyframes: {
        fadeSlideUp: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        pulseDot: {
          '0%, 60%, 100%': { opacity: '0.25', transform: 'scale(0.75)' },
          '30%':           { opacity: '1',    transform: 'scale(1)' },
        },
      },
      animation: {
        'fade-slide-up': 'fadeSlideUp 0.22s ease-out forwards',
        'dot-1': 'pulseDot 1.4s ease-in-out infinite',
        'dot-2': 'pulseDot 1.4s ease-in-out 0.18s infinite',
        'dot-3': 'pulseDot 1.4s ease-in-out 0.36s infinite',
      },
    },
  },
  plugins: [],
};

export default config;
