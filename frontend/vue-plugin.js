// A simple plugin to ignore Vue files
export default function vuePlugin() {
  return {
    name: 'vue-plugin',
    resolveId(id) {
      if (id.endsWith('.vue')) {
        return {
          id,
          external: true
        };
      }
      return null;
    }
  };
} 