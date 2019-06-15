Python API
----------

`cd` into the `python` directory.

To install dependencies (besides Python 3.6+):

```sh
pip install cbor2 falcon gunicorn h5py jsonschema numpy ruamel.yaml pytest
```

To run tests:

```sh
pytest
```


ArtisanUI
---------

`cd` into the `ui` directory.

To install dependencies (besides NodeJS, and the artisan dependencies, for testing):

```sh
npm install
```

To run the test server/client pair defined in the `test/` directory:

```sh
npm test
```


Documentation
-------------

`cd` into the root directory.

To install dependencies:

```sh
pip install sphinx sphinx_rtd_theme sphinx-autobuild jsx-lexer
```

To start the autobuild server:

```sh
sphinx-autobuild doc-src docs
```

This will make the documentation available at `localhost:8000`.
