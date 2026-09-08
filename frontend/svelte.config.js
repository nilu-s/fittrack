import adapter from '@sveltejs/adapter-node';
import staticAdapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: process.env.CRONICL_MOBILE === '1'
      ? staticAdapter({ pages: 'build-mobile', assets: 'build-mobile', fallback: 'index.html', strict: false })
      : adapter()
  }
};

export default config;
