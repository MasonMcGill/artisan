Using ArtisanUI
===============

ArtisanUI can be used to view artifacts exposed as a REST API via
``artisan.serve``. It supports custom views defined as a `React
<https://reactjs.org/>`_ components.


Getting started
---------------

Install `NodeJS <https://nodejs.org>`_, then run `npx artisan-ui` to start a
visualization server on `localhost:1234 <http://localhost:1234>`_.

*-- Screenshot --*

See `npm's documentation <https://docs.npmjs.com/cli/install>`_ for more
installation options.


Defining custom views
---------------------

ArtisanUI can be extended by pointing it to a Javascript module that exports a
configuration object. An example, with all of the supported fields:

.. code-block:: jsx

  // index.jsx

  import React from 'react'

  export default {
    /**
     * The default host to view
     */
    host: 'localhost:3000',

    /**
     * The time between automatic data refreshes, in milliseconds
     * (`null` disables automatic data refreshing.)
     */
    refreshInterval: 5000,

    /**
     * A custom view library, expressed as an array of `[pattern, view]` pairs.
     * When a page corresponding to an artifact is loaded, the first pair
     * matching the artifact's path is used. Patterns use the glob syntax
     * parsed by the `minimatch` library. Views can be React components or
     * arrays or React components.
     */
    views: [
      ['FooSimulation*', () => (
        <div>This is totally what an actual foo would do.</div>
      )],
      ['BarRegression*/errors', ({ app }) => (
        <pre>residuals: {app.fetch('residuals')}</pre>
      )],
      ['**', () => (
        <div>No specialized views to show</div>
      )]
    ]
  }

ArtisanUI uses `Parcel <https://parceljs.org/>`_ to bundle user-defined
extensions (supporting `Typescript <https://www.typescriptlang.org/>`_,
`ReasonML <https://reasonml.github.io/>`_, `SCSS <https://sass-lang.com/>`_, and
many other tools out of the box). Parcel detects dependencies declared in a
`package.json` file in the same directory as the extension module. Because
ArtisanUI already includes React and NumJs, they should be declared as
`peerDependencies`. *e.g.*

.. code-block:: json

  {
    "dependencies": {
      "lodash": "~4.17",
      "react-vis": "latest"
    },
    "peerDependencies": {
      "numjs": "*",
      "react": "*"
    },
    "private": true
  }


To run the modified ArtisanUI, pass the path to the extension module as an
argument:

.. code-block:: sh

  > npx artisan-ui index.jsx

*-- Screenshot --*


App API
-------

Custom views are rendered with an `app` property that allows them to access
ArtisanUI's functionality. `app` has the following members:

.. js:attribute:: params: object

  The parameters encoded in the page URL. `host` and `path` are defined by the
  root view, but other parameters can be defined to configure custom views.

.. js:attribute:: navigate(params: object): void

  Sets the application's parameters to the given object, updates the navbar's
  URL, and rerenders. This is generally less useful than `navUpdating`, but is
  included for completeness.

.. js:attribute:: navUpdating(updates: object): void

  Merges `updates` into the application's parameters, updates the navbar's URL,
  and rerenders. This can be called *e.g.* in a `<select>` element's `change`
  listener to change a view parameter, and have that change reflected in the URL
  (to facilitate sharing, bookmarking, *etc.*).

.. js:attribute:: fetch: Function

  Returns data from the data server, if it is available. Otherwise, ensures that
  the data has been requested, and suspends rendering until it has been loaded.

  Overloads
    **fetch**\(*path: string*): Resource
      Return the resource at the given path.
    **fetch**\(*paths: string[]*): Resource[]
      Return the resources at every path in an array of paths, as an analogous
      array (`paths[i]` corresponds to `resources[i]`).
    **fetch**\(*paths: {[key: string]: string}*): {[key: string]: Resource}
      Return the resources at every path in an object, as an analogous object
      (`paths[key]` corresponds to `resources[key]`).

  `ArrayFile`\s are fetched as NumJs arrays, `EncodedFile`\s are fetched as raw
  files, and `Artifact`\s are fetched as objects with fields corresponding to
  their entries. Metadata resources (*e.g.* `a/b/c/_entry-names` or
  `x/y/z/_meta`) are also returned as objects.

  Both absolute paths (`/path/from/root`) and relative paths
  (`path/from/current/artifact`) are supported.
