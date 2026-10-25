const nodeGlobals = {
  Buffer: "readonly",
  console: "readonly",
  process: "readonly",
  URL: "readonly",
  setTimeout: "readonly",
  clearTimeout: "readonly",
  fetch: "readonly",
};
const browserGlobals = {
  document: "readonly",
  window: "readonly",
  location: "readonly",
  history: "readonly",
  console: "readonly",
  URL: "readonly",
  HTMLElement: "readonly",
  HTMLButtonElement: "readonly",
  HTMLIFrameElement: "readonly",
  HTMLScriptElement: "readonly",
  SVGElement: "readonly",
  SVGSVGElement: "readonly",
  ResizeObserver: "readonly",
  requestAnimationFrame: "readonly",
  cancelAnimationFrame: "readonly",
  getComputedStyle: "readonly",
  CSS: "readonly",
  Event: "readonly",
};
const codeFiles = [
  ".claude/skills/learning-setup/scripts/**/*.mjs",
  ".claude/skills/learning-setup/assets/web/**/*.mjs",
  "tools/**/*.mjs",
  "tests/**/*.mjs",
];
export default [
  {
    ignores: [
      "node_modules/**",
      "build/**",
      "test-results/**",
      "playwright-report/**",
      ".foundation/**",
      ".claude/skills/learning-setup/vendor/**",
    ],
  },
  {
    files: codeFiles,
    languageOptions: { ecmaVersion: 2024, sourceType: "module" },
    linterOptions: { noInlineConfig: true, reportUnusedDisableDirectives: "error" },
    rules: {
      "no-unused-vars": "error",
      "no-undef": "error",
      "no-var": "error",
      "prefer-const": "error",
      eqeqeq: ["error", "always"],
      curly: ["error", "all"],
      "func-style": ["error", "declaration", { allowArrowFunctions: true }],
      "no-param-reassign": ["error", { props: true }],
      "max-depth": ["error", 4],
      "max-params": ["error", 4],
      "max-lines-per-function": ["error", { max: 120, skipBlankLines: true, skipComments: true }],
      "no-restricted-syntax": [
        "error",
        {
          selector: "ExportDefaultDeclaration",
          message: "CODE-01: named exportを使ってください。",
        },
      ],
    },
  },
  {
    files: [".claude/skills/learning-setup/scripts/**/*.mjs", "tools/**/*.mjs", "tests/**/*.mjs"],
    languageOptions: { globals: nodeGlobals },
  },
  {
    files: [".claude/skills/learning-setup/assets/web/**/*.mjs"],
    languageOptions: { globals: browserGlobals },
  },
];
