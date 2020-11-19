Working with contexts
=====================

An Artisan context is a collection of options that can be used to customize
target construction within a Python `execution context
<https://www.python.org/dev/peps/pep-0550/>`_. (Execution contexts generally
correspond to threads unless `asyncio
<https://docs.python.org/3/library/asyncio.html>`_ is being used.)



Context attributes
------------------

The following target-construction options exist:

- `root` (*Path*): The default directory for artifact creation, and the
  directory that will be searched for matches when an artifact is instantiated
  from a specification. By default, `root` is the current working directory.

- `scope` (*Mapping[str, type]*): The mapping used to resolve type names in
  specifications during target instantiation. By default, `scope` contains all
  non-Artisan-defined target types.

- `builder` (Callable[[Artifact, object], None]): The function called to write
  files into artifact directories. `builder` accepts two arguments, the artifact
  to construct and its specification. The default builder calls
  `artifact.__init__(spec)` and logs metadata to a `_meta_.json` file. Custom
  builders can log additional information or offload work to other processes to
  build artifacts in parallel.



Activating and retreiving contexts
----------------------------------

A new context can be activated using `artisan.push_context` or `artisan.using_context`:

.. code-block:: python3

  artisan.push_context(root='data')
  ... # Artifacts are created in 'data/'.
  artisan.pop_context()

  # This is equivalent:
  with artisan.using_context(root='data'):
      ... # Artifacts are created in 'data/'.

The currently active context can be retreived by calling `artisan.get_context`.

.. code-block:: python3

  context = artisan.get_context()
  context.root # => Path('.')
  context.scope # => <artisan._TargetTypeRegistry object>
  context.builder # => <function artisan._default_builder(artifact, spec)>



Generating JSON Schemas
-----------------------

Artisan provides functions to generate `JSON Schemas
<https://json-schema.org/>`_ describing the space of JSON-encodable objects that
will be recognized by `artisan.build` as valid specifications in the currently
active context. Tools like the `Visual Studio Code YAML extension
<https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml>`_ can
use these schemas to check for errors and provide suggestions when editing
JSON-like content that will be parsed as specifications, and tools like
`react-jsonschema-form
<https://react-jsonschema-form.readthedocs.io/en/latest/>`_ can use them to
generate HTML forms.

.. code-block:: python3

  artisan.get_spec_schema()      # describes valid artifact specs
  artisan.get_spec_list_schema() # describes lists of valid artifacts specs
  artisan.get_spec_dict_schema() # describes dictionaries of valid artifact specs

Type annotations in specification classes are converted to object property
schemas, public, non-callable class attributes are converted to "default"
annotations, docstrings are converted to "description" annotations, and `dict`
literals following attribute definitions/declarations are merged into the
schema.

.. code-block:: python3

  from typing import Protocol
  from artisan import Target

  class Tardigrade(Target):
      'A molecular-resolution simulation of a water bear.'

      class Spec(Protocol):
          temperature: float = 20.0; 'In degrees celsius.'
          environment: str; {'enum': ['outer space', 'volcano', 'pet shop']}

  artisan.get_spec_schema()['$defs']['Tardigrade']
  # => {
  #      'description': 'A molecular-resolution simulation of a water bear.'
  #      'type': 'object',
  #      'required': ['environment'],
  #      'properties': {
  #        'temperature': {
  #          'description': 'In degrees celsius.'
  #          'type': 'number',
  #          'default': 20.0
  #        },
  #        'environment': {
  #          'type': 'string',
  #          'enum': ['outer space', 'volcano', 'pet shop']
  #        }
  #      }
  #    }

`(str, dict)` and `(dict, str)` pairs work as well:

.. code-block:: python3

  class Toast(Target):
      class Spec(Protocol):
          temperature: float; {'minimum': 40.0}, "Otherwise, it's just bread."

Supported annotation types include `object`, `bool`, `int`, `float`, `str`,
`None`, `type(None)`, `Optional`, `Union`, `Literal`, `List`, `Path`, artifact
types, attribute-only protocols, and `Spec` types. `Spec` types of target types
with subclasses in the active scope are treated as type-tagged unions to support
polymorphism. *i.e.*,

.. code-block:: javascript

  Animal.Spec := {"type": "Cat", ...Cat.Spec} | {"type": "Dog", ...Dog.Spec}

To prevent ambiguity regarding concrete and abstract types, schemas only allow
specifications of target types without subclasses in the active scope to be
constructed. *i.e.*, specifications containing `{"type": "Animal"}` will be
rejected.
