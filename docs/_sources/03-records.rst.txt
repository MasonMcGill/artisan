Records
=======

A ``Record`` is an concurrency-safe, array-friendly view of a directory. Records support four types of data transactions: reading, writing, appending, and deleting.

Records pointing to directories created by ``Command``\ s also provide access to command metadata.

Obtaining a record
------------------

.. code-block:: python

  record = cg.Record('some/directory/path/')

Since a record is just a *view* into a directory, constructing it does not perform any filesystem operations. Files and directories are created lazily, even if the records' path does not exist.

Reading entries
---------------

Subscripting a record with a key corresponding to an HDF5 file (minus the extension) returns an array:

.. code-block:: python

  array = record['file/path']

Subscripting a record with a key corresponding to a non-HDF5 file returns the file's path (the file is presumed to be encoded in an application-specific format):

.. code-block:: python

  image_path = record['image/path.jpg']

Subscripting a record with a key corresponding to a directory returns a subrecord:

.. code-block:: python

  subrecord = record['directory/path']

Records also have `dict`-style iteration methods (``keys``, ``values``, and ``items``). These methods iterate over all entries in the directory corresponding to the record, with the exception of those with names beginning with "_".

Writing entries
---------------

Subscript-assigning can be used to write an array to a file.

.. code-block:: python

  record['file/path'] = array

Subscript-assigning can also be used to copy the contents of one record into another, deleting its previous contents.

.. code-block:: python

  record['directory/path'] = another_record

A [nested] `dict` of array-like objects can also be used to tersely write to multiple files.

.. code-block:: python

  record['beings/animals'] = {
    'dogs': {'snoopy': snoopy_data},
    'cats': {'garfield': garfield_data}}

Appending to entries
--------------------

Appending works analogously to writing, and creates files and directories as necessary.

.. code-block:: python

  record.append('file/path', array)
  record.append('directory/path', another_record)
  record.append('directory/path', dict_of_arrays)

Deleting entries
----------------

Deleting an entry removes files/directories recursively, from the key downward, and deletes empty parent directories, up to `record.path`. (In other words, deleting performs the inverse of the "create as necessary" operations writing performs.)

.. code-block:: python

  del record['some/path']

Accessing command metadata
--------------------------

Records also supports reading command metadata (stored in *_cmd-spec.yaml* and *_cmd-status.yaml*) via the ``cmd_spec`` and ``cmd_status`` properties.

Running a data server
---------------------

Records can also be accessed via HTTP. Currently, only `GET` operations are supported. Call ``serve`` to start a data server allowing clients to access the contents of a directory via a REST API.

.. code-block:: python

  # The following routes are supported:
  #  - /<record-path>/_entry-names
  #  - /<record-path>/_cmd-info
  #  - /<record-path>/<entry-name>
  #  - /<record-path>/<entry-name>?mode=file
  cg.serve('my-data/', port=5555)

When running the data server on a publicly accessible machine, `SSH tunneling <https://blog.trackets.com/2014/05/17/ssh-tunnel-local-and-remote-port-forwarding-explained-with-examples.html>`_ combined with `a firewall <https://help.ubuntu.com/community/UFW>`_ can be used to prevent public data access.
