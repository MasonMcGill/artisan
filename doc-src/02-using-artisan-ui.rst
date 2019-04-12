Using Artisan-UI
================

Artisan-UI can be used to view artifacts exposed as a REST API via ``artisan.serve``. It supports custom views defined as a `React <https://reactjs.org/>`_ components.

Artisan-UI can either be used as a standalone web application that can be started via a command-line interface, or as a React component that can be embedded into other applications. In either case, `NodeJS <https://nodejs.org>`_ must be installed to use Artisan-UI.


Using the Artisan-UI CLI
------------------------

*WIP*

- Setup

    - Example `package.json` file
    - Installing dependencies with npm
    - Running with npx

- Make a ".js" file
- "export selector = '.TypeName'"
- "export default Component(s)"
- Rationale: ".mdx" may be supported when tooling is mature

.. .. code-block:: json

..   {
..     "dependencies": {
..       "artisan-ui": "~0.1.0",
..       "react": "~16.8.0",
..       "react-dom": "~16.8.0"
..     },
..     "scripts": {
..       "serve-ui": "artisan-ui '*.js'"
..     }
..   }


Using the Artisan-UI API
------------------------

*WIP*

- Constructing a RootView


App object properties
---------------------

*WIP*

- params

    - "host" and "path" are reserved, but anything else can be used as view parameters

- navigate
- navUpdating
- `fetch` method

    - throws a Promise (suspending rendering) if the resource doesn't exist.
    - uses caching, but is automatically refreshed
    - supports arrays and objects with url elements