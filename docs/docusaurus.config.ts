import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Surge POS',
  tagline: 'High-performance Point of Sale for ERPNext',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://ujjwal-aggrawal2279.github.io',
  baseUrl: '/Surge-POS/',

  organizationName: 'Ujjwal-Aggrawal2279',
  projectName: 'Surge-POS',

  onBrokenLinks: 'throw',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/Ujjwal-Aggrawal2279/Surge-POS/edit/develop/docs/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Surge POS',
      logo: {
        alt: 'Surge POS Logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'guideSidebar',
          position: 'left',
          label: 'User Guide',
        },
        {
          href: 'https://github.com/Ujjwal-Aggrawal2279/Surge-POS',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Guide',
          items: [
            { label: 'Getting Started', to: '/docs/getting-started' },
            { label: 'Cashier Setup', to: '/docs/cashier-setup' },
            { label: 'Making a Sale', to: '/docs/making-a-sale' },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/Ujjwal-Aggrawal2279/Surge-POS',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Ujjwal Aggrawal. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'python'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
