Using Artisan
=============

.. currentmodule:: artisan

Broadly speaking, Artisan can be used to define artifact types, create instances
of them, and make those instances available via a REST API.


Defining artifact types
-----------------------

The following code block illustrates the components of an artifact type
definition.

.. code-block:: python3

  from pathlib import Path
  from artisan import Artifact, ArrayFile, EncodedFile

  ####
  # Artifact types should subclass `artisan.Artifact`.
  #
  class Greeting(Artifact):
      ''' [High-level description here] '''

      ####
      # (Optional) configuration class definitions are converted
      # to JSON-Schemas that document and validate artifact
      # configuration fields.
      #
      class Conf:
          name: str; 'A long-winded pointer'
          # -> {
          #   "type": " "string",
          #   "description": "A long-winded pointer"
          # }

          punctuation = '!'; 'Sets the mood', {'enum': ['!', '?']}
          # -> {
          #   "default": " "!",
          #   "description": "Sets the mood",
          #   "enum": ["!", "?"]
          # }

      ''' Additional docstrings throughout the class are collected
      after the class is defined. This allows documentation to be
      written in whatever way is best for readability. '''

      ####
      # String literals immediately following attribute-type annotations
      # are also added to the docstring, under the "Attributes" section
      # (which is created if it does not exist).
      #
      # Currently, `ArrayFile` is an alias for `h5py.Dataset` and
      # `EncodedFile` is an alias for `pathlib.Path`, but they may be
      # subclasses in the future.
      #
      message: ArrayFile; 'A friendly introduction'
      poems__txt: EncodedFile; 'Recommended poems'
      lucky_numbers: Artifact; 'Most fortunate integers, by day of the week'

      ####
      # `build` is called when an artifact is instantiated and the
      # corresponding files haven't yet been created. `build` should
      # define fields on `self`, writing files to the filesystem.
      #
      def build(self, c: Conf) -> None:
          ####
          # Assigning any object that can be converted to a NumPy
          # array to an attribute creates a single-dataset HDF5 file.
          # Subscript syntax (`self['key'] = value`) is also supported.
          #
          self.message = f'Hello, {c.name}{c.punctuation}.'.encode()

          ####
          # Array fields can also be extended. `extend` implicitly
          # creates a file if necessary.
          #
          self.extend('message', [b'Be not afraid.', b'I come in peace.'])

          ####
          # Assigning a path to a field copies the file at that
          # path to "{self.path}/{attr_name}". To support file
          # extensions, "__" is translated to "." in field names.
          #
          self.poems__txt = Path('where-the-sidewalk-ends.txt')

          ####
          # Accessing an attribute with "." or "__" in the name still
          # returns a path, even if nothing yet exists at that path.
          #
          self.poems2__txt.write_text(
              'Help me; I am trapped\n'
              'In a haiku factory.\n'
              'Save me before they'
          )

          ####
          # Encoded files can also be extended, performing
          # byte-level concatenation.
          #
          self.extend('poems__txt', Path('the-iliad.txt'))

          ####
          # Assigning a mapping to a field creates a subartifact.
          #
          self.lucky_numbers = dict(
              numbers_for_tuesdays = [2, 4, 8, 16],
              numbers_for_other_days = [1, 3, 6, 10]
          )

          ####
          # Extending subartifacts extends their fields.
          #
          self.extend('lucky_numbers', dict(
              numbers_for_tuesdays = [ord(c.name[0])],
              numbers_for_other_days = []
          ))

          ####
          # Accessing an attribute without "." or "__" in the name
          # returns an empty Artifact.
          #
          assert (
              isinstance(self.empty_dir, Artifact)
              and len(self.empty_dir) == 0
          )


Instantiating artifacts
-----------------------

Artifacts can be constructed from specifications with fields corresponding to
their expected configuration fields.

.. code-block:: python

  Greeting(name='Sven', punctuation='!')
  Greeting({'name': 'Sven', 'punctuation': '!'}) # Equivalent

This returns a matching artifact, if it already exists, and otherwise creates
one. Specifications can also include a "type" field, indicating what type of
artifact to construct (see *Nested configurations* for more details).

.. code-block:: python

  Artifact(type='Greeting', name='Sven', punctuation='!') # returns a Greeting

Existing artifacts can also be loaded by their paths.

.. code-block:: python

  Greeting('Greeting_0000')

Providing a path *and* a specification returns a matching artifact, if it
exists at that path, and otherwise creates one, at that path.

.. code-block:: python

  Greeting('greetings/hello4sven', name='Sven', punctuation='!')

An error is raised if incompatible files/directories already exist at the
specified path.


In-memory components
--------------------

Non-serialized configurable objects can be created by subclassing
`artisan.Configurable`. Configurable objects support `Conf` class definitions
and flexible docstring authoring (artifacts inherit these properties from
`Configurable`), but their items/attributes aren't backed by the filesystem.


Global configuration
--------------------

The following thread-local configuration options exist:

- `root_dir` (*str|Path*): The directory in which artifacts are created by
  default. When artifact instantiation searches for a matching directory, it
  performs a shallow search in `root_dir`. By default, the current working
  directory.
- `scope` (*{str: type}*): The mapping `Configurable` instantiation uses to
  resolve types, when a specification includes a "type" field. By default, the
  set of all defined `Configurable` subtypes, whose names don't start with an
  underscore, keyed by their names (if this produces a name clash that leads to
  an ambiguous lookup, an error is raised).

Thread-local configuration options can be manipulated via the `push_conf`,
`pop_conf`, and `using_conf` functions.

.. code-block:: python

  artisan.push_conf(root_dir='data')
  ... # <create artifacts in 'data/'>
  artisan.pop_conf()

  # Or, equivalently
  with artisan.using_conf(root_dir='data'):
      ... # <create artifacts in 'data/'>


Configuration schema details
----------------------------

Configuration-class entries define `JSON-Schema <https://json-schema.org/>`_
object property schemas.

- Identifier definitions are translated to property names.
- Type annotations are translated to "type", and sometimes "items", constraints.
  Supported types include `bool`, `int`, `float`, `str`, `NoneType`,
  artifact or component configuration types (*e.g.* `Greeting.Conf`), and
  `typing.List` specializations of other supported types
  (*e.g.* `List[int]`).
- Assignments (*e.g.* `x = 1`) add "default" fields.
- `str` literals following definitions add "description" fields.
- `dict` literals following definitions are merged into the schema.
  `(str, dict)` and `(dict, str)` literal pairs are also supported.

A configurating entry matching `<SomeArtifactType>.Conf` must

- have a "type" field resloving, in the current `scope`, to a subclass of
  `<SomeArtifactType>`, and
- have every field required by that subclass' configuration schema.


Generating a REST API
---------------------

Artifacts can be exposed as a REST API by calling `serve`.

.. code-block:: python

  artisan.serve(4000) # Serves the contents of `root_dir` on port 4000
  artisan.serve(4001, 'data') # Serves the contents of "data/" on port 4001

The REST API supports the following route forms:

- **path/to/array**: A CBOR-encoded array
- **path/to/file.ext**: A raw file
- **path/to/artifact**: A CBOR-encoded object mapping entry names to contents
  (objects in the case of array/subartifact entries, and strings---paths
  relative to `root_dir`---for non-array files)
- **path/to/artifact/_entry-names**: A CBOR-encoded object mapping entry names
  to small metadata objects
- **path/to/artifact/_meta**: The contents of *meta.yaml*, CBOR-encoded
