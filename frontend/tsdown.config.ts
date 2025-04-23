import { defineConfig } from 'tsdown';
import vuePlugin from './vue-plugin.js';

export default defineConfig({
  entry: ['src/main.js'],
  format: ['esm', 'cjs'],
  dts: true,
  minify: true,
  outDir: 'dist',
  external: ['vue'],
  plugins: [vuePlugin()]
}); 