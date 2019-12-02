Working with configurable objects
=================================

Any type whose constructor accepts a `JSON-object-like configuration
<#configurations>`_ as its first argument can subclass `artisan.Configurable`
for additional features, including

- a `configuration class <#configuration-classes>`_ describing the space of
  valid configurations, if one is not already defined,

- a `JSON-schema <https://json-schema.org/>`_ derived from its configuration class,

- support for an `extended docstring syntax <#the-extended-docstring-syntax>`_,

- a default constructor, and

- `subclass forwarding`_, a mechanism by which a configuration can specify an
  object's type.

.. - support for defining configuration classes
.. - subclass forwarding
.. - complementary convenience features like a default constructor and an
..   extended docstring syntax

.. code-block:: python3

  #-- A general usage example --#
  from glob import glob
  from artisan import Configurable
  import cv2 as cv, numpy as np

  class ImageGenerator(Configurable):
      ''' Produces images with a given height and width '''

      class Conf:
          source: str; 'The path to a directory containing PNG images'
          height: int = 786; 'Image height, in pixels', {'minimum': 1}
          width: int = 1024; 'Image width, in pixels', {'minimum': 1}

      def sample(self) -> np.ndarray:
          'Return a random image in `conf.source`.'
          img = cv.imread(np.random.choice(glob(f'{self.conf.source}/*.png')))
          return cv.resize(img, (self.conf.height, self.conf.width))

  gen = ImageGenerator({'source': './aardvark-pictures', 'height': 512})
  gen.sample() # -> <A 512×1024-pixel aardvark>


Configurations
--------------

A configuration can be any string-keyed mapping containing arbitrarily nested
`bool`, `int`, `float`, `str`, `NoneType`, sequence, and string-keyed mapping
instances. `Configurable.__new__` stores the configuration passed into it as a
`Namespace` (a dictionary that supports accessing items as attributes),
accessible as `<obj>.conf`.


Configuration classes
---------------------

A `Configurable` subclass can define an inner `Conf` class specifying the space
of configurations it accepts. If no `Conf` class is defined, an empty one is
generated.

Statically, a `Conf` class acts as a `protocol
<https://mypy.readthedocs.io/en/latest/protocols.html>`_ (though subclassing
`typing_extensions.Protocol` is optional). At runtime, it is used to generate a
JSON-schema, which can be accessed as `<cls>.conf_schema`. Configurations passed
into the `Configurable` subclass' constructor are checked against this schema.

.. code-block:: python3

  class SolarSystem(Configurable):
      ''' An N-body simulation where you can give the planets
          cute names like "Rocky" or "Frederick" '''

      class Conf:
          planet_names: List[str]; 'Long-winded pointers'
          dt: float = 0.01; 'Timestep duration, in days', {'minimum': 1e-6}
          integrator: some_module.Integrator.Conf; 'How to do all the hard math'

  SolarSystem.conf_schema
  # -> {
  #   'definitions': { ... },
  #   'type': 'object',
  #   'description': (
  #     ' An N-body simulation where you can give the planets\n'
  #     '        cute names like "Rocky" or "Frederick" '
  #   ),
  #   'properties':
  #     'planet_names': {
  #       'type': 'array',
  #       'items': {'type': 'string'},
  #       'description': 'Long-winded pointers'
  #     },
  #     'dt': {
  #       'type': 'number',
  #       'default': 0.01,
  #       'description': 'Timestep duration, in days',
  #       'minimum': 1e-6
  #     },
  #     'integrator': {
  #       '$ref': '#/definitions/Integrator',
  #       'description': 'How to do all the hard math'
  #     }
  #   },
  #   'required': ['planet_names', 'integrator']
  # }

  SolarSystem({'planet_names': ['Orcus', 'Minerva'], 'integrator': {'kind': 'euler'}}) # Valid
  SolarSystem({'planet_names': ['Orcus', 'Minerva'], 'integrator': 'oyler'}) # Raises an error


Schema-generation rules
-----------------------

The top-level statements in a configuration class definition are translated to
object property schemas via the following rules:

- Identifier definitions in assignment or type annotation statements specify
  property names.

- Type annotations are translated to "type", "items", or "$ref" fields.
  Supported types include `bool`, `int`, `float`, `str`, `NoneType`, `object`,
  configuration types, and `typing.List` or `typing.Dict[str, T]`
  specializations of other supported types.

- Assignments add "default" fields.

- `str` literals following definitions add "description" fields.

- `dict` literals following definitions are merged into the schema.
  `(str, dict)` and `(dict, str)` literal pairs are also supported.

To eliminate ambiguity regarding which types are safe to construct, configurable
object types with subclasses are assumed to be abstract. The `conf_schema` of
such a class corresponds to a type-tagged union of the `conf_schema`\s of its
subtypes. (See `subclass forwarding`_ for more information about type tagging.)


The extended docstring syntax
-----------------------------

A `Configurable` subclass' `__doc__` attribute is constructed from all of the
top-level string literals in the class body, besides those immediately following
an assignment or type declaration statement (these are instead placed in an
`__attr_docs__` dictionary, similar in spirit to `PEP 224
<https://www.python.org/dev/peps/pep-0224/>`_). This allows configuration class
definitions to be placed towards the beginning of the class description, where
parameter documentation is often written.

.. code-block:: python3

  class Tardigrade(Configurable):
      ''' A molecular-resolution simulation of a water bear '''

      class Conf:
          temperature: float; 'in degrees celsius'
          environment: str; {'enum': ['outer space', 'volcano', 'pet shop']}

      molecules: List[Molecule]; 'The physical components of this tardigrade'
      feelings: List[Feeling]; 'The emotional components of this tardigrade'

      ''' A hearty and noble beast, *Milnesium tardigradum* spends its day
      grazing on algae and mastering the art of survival... '''

  Tardigrade.__doc__
  # -> (
  #   ' A molecular-resolution simulation of a water bear \n'
  #   '\n'
  #   ' A hearty and noble beast, *Milnesium tardigradum* spends its day\n'
  #   '    grazing on algae and mastering the art of survival... '
  # )

  Tardigrade.__attr_docs__
  # -> {
  #   'molecules': 'The physical components of this tardigrade',
  #   'feelings': 'The emotional components of this tardigrade'
  # }

Attribute docstrings may be exposed via `conf_schema`\s in a future release.


Subclass forwarding
-------------------

Calling a `Configurable` subclass' constructor with a configuration with a
"type" field will yield an instance of the corresponding type.

.. code-block:: python

  class Animal(Configurable):
      pass

  class Bat(Animal):
      class Conf:
          wingspan: float; 'in inches'
          has_vampirism = False

  class Capybara(Animal):
      class Conf:
          tooth_length: float; 'also in inches'

  Animal({'type': 'Bat', 'wingspan': 6.0}) # Constructs a bat
  Animal({'type': 'Capybara', 'tooth_length': 2.3}) # Constructs a capybara
  Animal() # Raises an error

By default, all `Configurable` subclasses are identified by their
`__qualname__`. The scope mapping names to types can be configured via the
`Artisan <configuring-artisan.html>`_ API.

.. code-block:: python

  with Artisan(scope={'FlutterMouse': Bat, 'WaterPig': Capybara}):
      Animal(type='WaterPig', tooth_length=2.3) # Constructs a capybara
