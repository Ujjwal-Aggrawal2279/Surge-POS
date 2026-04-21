import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  guideSidebar: [
    {
      type: 'category',
      label: 'Getting Started',
      items: ['getting-started', 'installation', 'configuration'],
    },
    {
      type: 'category',
      label: 'Daily Operations',
      items: ['cashier-setup', 'making-a-sale', 'payments', 'returns-voids'],
    },
    {
      type: 'category',
      label: 'Administration',
      items: ['pos-profile', 'item-catalog', 'reports'],
    },
    {
      type: 'category',
      label: 'Reference',
      items: ['keyboard-shortcuts', 'troubleshooting'],
    },
  ],
};

export default sidebars;
