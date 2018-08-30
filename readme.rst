CommandGraph
============

CommandGraph is a small set of complimentary tools for exploratory computational research. It provides functionality to simplify the following tasks:

- Routing, validating, and storing command configurations
- Keeping track of command states and executing command dependencies when necessary
- Storing and accessing command outputs
- Generating command-line and web-based user interfaces

The full documentation is available `here <https://masonmcgill.github.io/cmdgraph/>`_.

Design
------

CommandGraph attempts to provide a minimal, coherent interface based on standard, cross-language technologies, including

- `YAML <http://yaml.org/>`_/`JSON <https://www.json.org/>`_ for configuration authoring
- `JSON-Schema <http://json-schema.org/>`_ for configuration validation
- `HDF5-SWMR <http://docs.h5py.org/en/latest/swmr.html>`_ for concurrency-safe array serialization, and
- `REST/HTTP <https://en.wikipedia.org/wiki/Representational_state_transfer>`_ for exploring command outputs.

It should take a few minutes to learn and a few days to rewrite in your favorite programming language.

Installation
============

.. code-block:: shell

  > pip install cmdgraph

`Conda <https://conda.io/docs/>`_ works as well. CommandGraph requires Python ≥3.6.

Commands
========

To CommandGraph, a ``Command`` is an object that writes files to a directory, based on a configuration and/or the outputs of other commands.

Defining commands
-----------------

A minimal command with input and output looks like this:

.. code-block:: python

  import cmdgraph as cg

  class SayHello(cg.Command):
    output_path = 'greetings/{name}' # Config fields are substituted automatically
                                     # (though using this shorthand is optional).
    def run(self):
      self.output['message.h5'] = (  # Records provide a concurrency-safe,
        f'Hello, {self.conf.name}!') # array-friendly view into the filesystem.

  SayHello(name='Sven')() # This writes "Hello, Sven!" to /greetins/Sven/message.h5,
                          # and writes metadata to /greetings/Sven/_cmd-spec.yaml
                          # and /greetings/Sven/_cmd-status.yaml.

Accessing command metadata
--------------------------

``cmd.spec`` returns a command's specification---its configuration, augmented with a field encoding its type---as a JSON-like object (an arbitrarily nested combination of `bool`, `int`, `float`, `str`, `NoneType`, `list`, and `SimpleNamespace` instances).

``cmd.status`` returns the command's execution status: *“running”*, *“done”*, *“stopped”*, or *“unbegun”*.

.. todo::

  Reimplement `cmd.spec`.

Executing commands
------------------

Calling a command (``cmd()``) invokes it unconditionally.

``require`` invokes the command if necessary and blocks until it has finished executing. It does nothing if the command's status is "done".

.. code-block:: python

  class WarpCatPictures(cg.Command):
    output_path = 'warped-cats'

    def run(self):
      cats = cg.require(GetCats(source='the-internet')) # `require` returns the dependent
      self.output['result.png'] = warp_thoroughly(cats) # command's output record.

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

Subscripting a record with a key corresponding to a file returns an array:

.. code-block:: python

  array = record['file/path.h5']

HDF5 (".h5"), JPEG (".jpg"/".jpeg"), PNG (".png"), and bitmap (".bmp") formats are currently supported. Files with other extensions are treated as plain text files. Open a GitHub issue or pull request to request new format support.

Subscripting a record with a key corresponding to a directory returns a subrecord:

.. code-block:: python

  subrecord = record['directory/path/']

Records also have `dict`-style iteration methods (``keys``, ``values``, and ``items``). These methods iterate over all entries in the directory corresponding to the record, with the exception of those with names beginning with "_".

Writing entries
---------------

Subscript-assigning can be used to write an array to a file.

.. code-block:: python

  record['file/path.h5'] = array

Subscript-assigning can also be used to copy the contents of one record into another, deleting its previous contents.

.. code-block:: python

  record['directory/path/'] = another_record

A [nested] `dict` of array-like objects can also be used to tersely write to multiple files.

.. code-block:: python

  record['beings/animals/'] = {
    'dogs': {'snoopy.h5': snoopy_data},
    'cats': {'garfield.png': garfield_data}}

Appending to entries
--------------------

Appending works analogously to writing, and creates files and directories as necessary.

.. code-block:: python

  record.append('file/path.h5', array)
  record.append('directory/path/', another_record)
  record.append('directory/path/', dict_of_arrays)

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

Configuration management
========================

CommandGraph ``Command``\ s are ``Configurable`` objects, which means they can be constructed from JSON-like objects and support configuration schema specification (to document and validate configuration fields).

Non-command configurable objects can be defined as well, which can be useful when components are shared between multiple commands:

.. code-block:: python

  class Muppet(cg.Configurable):
    ...

  kermit = Muppet(color='green', has_it_easy=False)

Configurable object properties
------------------------------

An object's configuration can be accessed via ``obj.conf``. ``obj.spec`` provides its specification: its configuration augmented with a field indicating its type.

.. code-block:: python

  kermit.conf # => Namespace(color='green', has_it_easy=False)
  kermit.spec # => Namespace(color='green', has_it_easy=False, type='__main__/Muppet')

Creating objects from specifications
------------------------------------

Objects can be instantiated from specifications using the ``create`` function. This can be helpful when instantiating configurable objects within commands.

.. code-block:: python

  class PutOnAShow(cg.Command):
    def run(self):
      muppet = cg.create(self.conf.muppet)
      print(muppet.tell_a_joke())

  PutOnAShow(muppet=load_muppet_spec())()

Defining namespaces
-------------------

By default, the `type` field in an object's specification is derived from it's type's name and module path, which may be volatile over the course of a project's development. This limits the usefulness of stored specifications.

Entering a ``Namespace`` can override this default behavior with more stable (and often more readable) bindings:

.. code-block:: python

  with cg.Namespace({'Muppet': a.b.c.Something}):
    a.b.c.Something().spec # => Namespace(type='Muppet')

.. todo::

  Fix the "conflicting meanings of namespace" issue. Maybe `types.SimpleNamespace` should be dropped in favor of `dict`\ s? Maybe `cg.Namespace` should be called `cg.Scope`?

Defining schemas
----------------

Override a configurable type's ``Conf`` class to specify a configuration schema.

Members of `Conf` are interpreted in the following way:

- The member's name corresponds to the expected property's name.
- A `type` value specify the property's expected type.
- A single-element `list` value specifies the property's default value.
- A `str` value specifies the property's docstring.
- A `tuple` value may specify any combination of the above.

Example:

.. code-block:: python

  class Person(cg.Configurable):
    class Conf:
      name = str, 'a long-winded pointer'
      age = int, [0], 'solar rotation count'
      shoe_size = 'European standard as of 2018-08-17'

Defining configuration schemas is completely optional, but it enables configuration validation and provides nice documentation, both in the code, and in CommandGraph-generated web and command-line interfaces.

.. todo::

  Make config schemas available as JSON-like objects.

.. todo::

  Expose schemas in the web interface.

Generating a command-line interface
-----------------------------------

``cli`` generates a command-line interface exposing every function in the current namespace stack.

.. code-block:: python

  # Generates the branching interface
  #   `<this-file> {a|b} [<conf>]`.
  with cg.Namespace({'a': DoA, 'b': DoB}):
    cg.cli()

Related packages
================

- `Luigi <https://luigi.readthedocs.io/en/stable/>`_ focuses on managing large, complex graphs of commands, possibly distributed across multiple machines. From the developers: *"Luigi is a Python module that helps you build complex pipelines of batch jobs. It handles dependency resolution, workflow management, visualization etc. It also comes with Hadoop support built in."*
- `Sacred <https://pypi.org/project/sacred/>`_ focuses on configuration management and random number generator seed control. It's more oriented towards writing scripts than writing APIs. From the developers: *"Sacred is a tool to help you configure, organize, log and reproduce experiments."*
- `GNU Make <https://www.gnu.org/software/make/>`_. Sometimes it's best to just keep things simple : )
