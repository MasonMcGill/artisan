# ArtisanUI

ArtisanUI is a visual interface for Artisan. See the main documentation site for
more details.

## File overview

- **package.json:** Metadata for [npm](https://npmjs.com).

- **rollup.config.js:** The [Rollup](https://rollupjs.org/guide/en) configuration
  used to transform *index.tsx* into *dist/index.js*. Bundles non-external
  dependencies, erases type annotations, and converts
  [JSX](https://reactjs.org/docs/introducing-jsx.html) expressions to standard
  Javascript.

- **cli:** The command-line interface exposed (as `artisan-ui`) when ArtisanUI is
  installed via npm. `artisan-ui serve ...` starts a hot-reloading development
  server and `artisan-ui build ...` (coming soon!) builds a static site.

- **index.{html|tsx|css}:** Assets used (directly or indirectly) by *cli* to
  build/serve the ArtisanUI web app.

## Testing

Install [NodeJS](https://nodejs.org/en/) and run `npm install` to install
dependencies.

Run `npm run watch` in the *artisan/ui* directory to start a watcher that
updates *dist/index.js* whenever *index.tsx* changes.

To run external tests, run `npm link` in the *artisan/ui* directory. This will
make the `artisan-ui` command available as it would be if ArtisanUI was
installed from npm/GitHub/*etc.*
