Generating a REST API
=====================

The `API` class can be used to expose an Artisan context via HTTP:

.. code-block:: python3

  #-- rest.py --#
  from artisan import API

  api = API()

  if __name__ == '__main__':
      api.serve(port=8000)

APIs can also be used with third-party `WSGI servers
<https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface>`_ like `Gunicorn
<https://gunicorn.org/>`_, which supports useful features like worker pools and
hot-reloading:

.. code-block:: sh

  > gunicorn rest:api --workers=8 --reload

By default, an API exposes the context in which it is constructed, but context
attributes can be overridden by passing options to the API constructor:

.. code-block:: python3

  api = API(root = 'path/to/artifacts', # overrides `<active_context>.root`
            scope = {'DataBlob': my_lib.DataBlob}, # overrides `<active_context>.scope`
            builder = my_lib.bespoke_artifact_builder) # overrides `<active_context>.builder`



Supported request types
-----------------------

- `GET /artifacts{/path-to-file*}`: Responds with the file at the specified
  path, relative to the context's root directory. The path's extension is
  inferred. A `"Last-Modified" header
  <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Last-Modified>`_ is
  provided and `"If-Modified-Since" request headers
  <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-Modified-Since>`_
  are supported. Contiguous `range requests
  <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Range>`_ are also
  supported.

- `GET /artifacts{/path-to-directory*}`: Responds with a shallow, CBOR-encoded
  description of the artifact at the specified path, relative to the context's
  root directory. The path's extension is inferred. The response body is a
  mapping with (1) a "_meta_" key mapped to the contents of the artifact's
  `_meta_.json` file, if it exists, and `null`, otherwise, and (2) keys
  corresponding to every public attribute in the corresponding artifact, mapped
  to `null`. A "Last-Modified" header is provided and "If-Modified-Since"
  request headers are supported.

- `POST /artifacts`: Creates a new artifact from a CBOR-encoded specification
  (the request body), if it does not already exist.

- `DELETE /artifacts{/path*}`: Deletes the artifact or artifact entry at the
  specified path, relative to the context's root directory. The path's extension
  is inferred.

- `GET /schemas/spec`: Responds with `artisan.get_spec_schema()`, as a JSON
  object.

- `GET /schemas/spec-list`: Responds with `artisan.get_spec_list_schema()`, as a
  JSON object.

- `GET /schemas/spec-dict`: Responds with `artisan.get_spec_dict_schema()`, as a
  JSON object.

- `GET /ui{/path*}`: Responds with a :ref:`user-interface resource<Generating a
  web UI>`.

Analogous `HEAD` and `OPTIONS` requests are also supported.


Authentication
--------------

APIs can be constructed with a `permissions` argument to add password protection:

.. code-block:: python3

  api = API(permissions={
      '🗝🔑🗝🔑🗝': {'read'}, # OPTIONS, HEAD, and GET access
      '0pen_5esame': {'read', 'write'}, # OPTIONS, HEAD, GET, and POST access
      'correct-cheval-batterie-agrafe': {'read', 'write', 'delete'}}) # Full access

`permissions` is a mapping from passwords to permission sets. Every entry in
`permissions` grants the specified permissions to clients that provide the
specified password. Passwords must be provided as `authentication headers
<https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Authorization>`_
using the `"Basic" authentication scheme
<https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication#Basic_authentication_scheme>`_
(IETF RFC 7617) with an empty username. Permissions sets can contain "read",
"write", and/or "delete". The default permission policy is `{'': ('read',
'write', 'delete')}`, meaning even users who have not provided a password have
"read", "write", and "delete" permissions.

`permissions` can only provide a reasonable level of security if the API is
exposed via HTTPS. `Let's Encrypt <https://letsencrypt.org/getting-started/>`_
provides free digital certificates that can be used to serve HTTPS applications.



.. Fetching arrays
.. ---------------

.. A `GET` request to an extensionless path corresponding to a single-array HDF5
.. file yields a `CBOR <https://cbor.io/>`_-encoded response with the following
.. fields:

.. - `type`: *"ArrayFile"*

.. - `dtype`: *"uint8"*, *"uint16"*, *"uint32"*, *"int8"*, *"int16"*, *"int32"*, *"float32"*,
..   *"float64"*, or *"string"*

.. - `shape`: The array's shape, as an array of integers

.. - `data`: The elements, in C-contiguous order, as a binary array or string array

.. - `timestamp`: The file's last modification timstamp, as an integer

.. If the query parameter `t_last` is provided and its value is greater than or
.. equal to the corresponding file's last modification timestamp, the response's
.. type will instead be *"CachedValue"* and the other fields will be omitted.


.. Fetching raw files
.. ------------------

.. A `GET` request to a path corresponding to a file, including the extension,
.. yields the file's raw data, suitable for use in `<img>`, `<video>`, and
.. `<audio>` tags.

.. In addition to files present in the artifact root directory, a virtual file,
.. `_schema.json`, which contains a configuration schema derived from the current
.. scope, is available as well. Having access to this schema can be useful when
.. working with tools like Visual Studio Code's `JSON
.. <https://code.visualstudio.com/docs/languages/json>`_ and `YAML
.. <https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml>`_
.. packages.


.. Fetching artifact metadata
.. --------------------------

.. A `GET` request to a path corresponding to a directory yields a CBOR-encoded
.. response with the following fields:

.. - `type`: *"Artifact"*

.. - `conf`: The artifact's configuration, as an object, or `null`

.. - `status`: *"running"*, *"done"*, *"stopped"*, or `null`

.. - `entries`: An object mapping entry names to entry summaries with the fields

..   - `type`, `shape`, and `dtype` for array files,
..   - `type` and `size` (in bytes) for other files, and
..   - `type`, `conf`, `status`, and `nEntries` for subdirectories
