Using ArtisanUI
===============

ArtisanUI can be used to view artifacts exposed as a REST API via
``artisan.serve``. It supports custom views defined as a `React
<https://reactjs.org/>`_ components.

Quick start
-----------

Install `NodeJS <https://nodejs.org>`_, then run `npx artisan-ui` to start a
visualization server and open *localhost:1234* in a web browser to use it.


Defining custom views
---------------------

Create a `package.json` file with the following contents:

.. code-block:: json

  {
    "dependencies": {
      "react": "latest"
    },
    "private": true
  }

Add any other `npm <https://npmjs.com>`_ packages you'd like to use to the
"dependencies" object, then install the project's dependencies by running
`npm install`.

Next, create `index.jsx`:

.. code-block:: jsx

  export default {
    views: [
      ["*", () => <h1>Test</h1>]
    ]
  }


Then, run

.. code-block:: sh

  > npx artisan-ui index.jsx


Defining custom views
---------------------

- "export selector = '.TypeName'"
- "export default Component(s)"
- Rationale: ".mdx" may be supported when tooling is mature


App object properties
---------------------

*WIP*

- params

    - "host" and "path" are reserved, but anything else can be used as view
      parameters

- navigate
- navUpdating
- `fetch` method

    - throws a Promise (suspending rendering) if the resource doesn't exist.
    - uses caching, but is automatically refreshed
    - supports arrays and objects with url elements