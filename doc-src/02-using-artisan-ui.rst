Using Artisan-UI
================

- Installing node


Using the Artisan-UI CLI
------------------------

- Setup

    - Example `package.json` file
    - Installing dependencies with npm
    - Running with npx

- Make a ".js" file
- "export selector = '.TypeName'"
- "export default Component(s)"
- Rationale: ".mdx" may be supported when tooling is mature


Using the Artisan-UI API
------------------------

- Constructing a RootView


App object properties
---------------------

- params

    - "host" and "path" are reserved, but anything else can be used as view parameters

- navigate
- navUpdating
- `fetch` method

    - throws a Promise (suspending rendering) if the resource doesn't exist.
    - uses caching, but is automatically refreshed
    - supports arrays and objects with url elements