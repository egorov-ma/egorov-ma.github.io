import { defineConfig } from 'astro/config';

// Адрес сайта; после подключения своего домена заменить на него
export default defineConfig({
  site: 'https://egorov-ma.github.io',
  trailingSlash: 'ignore',
  build: { format: 'directory' },
});
