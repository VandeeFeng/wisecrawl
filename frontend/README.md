# tsdown Configuration for Vue

This project uses tsdown for bundling TypeScript while properly handling Vue Single File Components.

## Configuration

We've set up a custom Vue plugin to mark .vue files as external during the build process. This prevents tsdown from trying to process Vue files directly, which would otherwise cause errors.

### Files
- `vue-plugin.js`: A simple plugin that marks Vue files as external
- `tsdown.config.ts`: Configuration file for tsdown that uses the plugin

### How it works
The plugin intercepts any imports ending with `.vue` and marks them as external, allowing the bundler to skip processing them directly.

## Building
Run the build with:
```
npm run build:tsdown
```

This will generate output in the `dist` directory. 