Generating a REST API
=====================

The `API` class can be used to expose the current artisan context via HTTP.

.. code-block:: python3

  #-- api.py --#
  from artisan import Artisan, API

  Artisan.push(
      root_dir = 'path/to/artifacts',
      scope = {
           # Add exported types here.
      }
  )

  API().serve(port=8000)

APIs can also be used with `WSGI servers
<https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface>`_ like `Gunicorn
<https://gunicorn.org/>`_, to add support for useful features like
worker pools and hot-reloading (accessible through Gunicorn's `--workers` and
`--reload` options, respectively).

.. code-block:: python3

  wsgi_app = API() # Run with `gunicorn api:wsgi_app`.


Fetching arrays
---------------

A `GET` request to an extensionless path corresponding to a single-array HDF5
file yields a `CBOR <https://cbor.io/>`_-encoded response with the following
fields:

- `type`: *"ArrayFile"*

- `dtype`: *"uint8"*, *"uint16"*, *"uint32"*, *"int8"*, *"int16"*, *"int32"*, *"float32"*,
  *"float64"*, or *"string"*

- `shape`: The array's shape, as an array of integers

- `data`: The elements, in C-contiguous order, as a binary array or string array

- `timestamp`: The file's last modification timstamp, as an integer

If the query parameter `t_last` is provided and its value is greater than or
equal to the corresponding file's last modification timestamp, the response's
type will instead be *"CachedValue"* and the other fields will be omitted.


Fetching raw files
------------------

A `GET` request to a path corresponding to a file, including the extension,
yields the file's raw data, suitable for use in `<img>`, `<video>`, and
`<audio>` tags.

In addition to files present in the artifact root directory, a virtual file,
`_schema.json`, which contains a configuration schema derived from the current
scope, is available as well. Having access to this schema can be useful when
working with tools like Visual Studio Code's `JSON
<https://code.visualstudio.com/docs/languages/json>`_ and `YAML
<https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml>`_
packages.


Fetching artifact metadata
--------------------------

A `GET` request to a path corresponding to a directory yields a CBOR-encoded
response with the following fields:

- `type`: *"Artifact"*

- `conf`: The artifact's configuration, as an object, or `null`

- `status`: *"running"*, *"done"*, *"stopped"*, or `null`

- `entries`: An object mapping entry names to entry summaries with the fields

  - `type`, `shape`, and `dtype` for array files,
  - `type` and `size` (in bytes) for other files, and
  - `type`, `conf`, `status`, and `nEntries` for subdirectories
