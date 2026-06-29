// @ts-check
const { themes: prismThemes } = require("prism-react-renderer");

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "LongHaulC2",
  tagline: "Long-haul persistent access management.",
  url: "https://longhaulc2.github.io",
  baseUrl: "/",
  organizationName: "LongHaulC2",
  projectName: "LongHaulC2",

  onBrokenLinks: "warn",
  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: "warn",
    },
  },
  themes: ["@docusaurus/theme-mermaid"],

  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },

  presets: [
    [
      "classic",
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          // Docs live right here alongside this config file.
          path: ".",
          routeBasePath: "/",
          sidebarPath: "./sidebars.js",
          // Exclude everything that isn't a markdown doc.
          exclude: [
            "**/node_modules/**",
            "**/build/**",
            "**/.docusaurus/**",
            "**/src/**",
            "**/static/**",
          ],
        },
        // Blog is not used.
        blog: false,
        theme: {
          customCss: "./src/css/custom.css",
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        defaultMode: "dark",
        disableSwitch: false,
        respectPrefersColorScheme: false,
      },

      navbar: {
        title: "LongHaulC2",
        items: [
          {
            type: "docSidebar",
            sidebarId: "docs",
            position: "left",
            label: "Docs",
          },
          {
            href: "https://github.com/LongHaulC2/LongHaulC2",
            label: "GitHub",
            position: "right",
          },
        ],
      },

      footer: {
        style: "dark",
        copyright: `LongHaulC2 — Built with Docusaurus.`,
      },

      prism: {
        theme: prismThemes.dracula,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ["bash", "json", "cpp", "python"],
      },
    }),
};

module.exports = config;
