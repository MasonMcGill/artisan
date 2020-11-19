.. py:currentmodule:: artisan



Working with targets
====================

Artisan allows CLI, REST API, and web UI users to construct objects called
"build targets", or "targets", for short. New target types can be created by
extending `artisan.Target`. Target construction can be customized via
user-defined specification objects, and target types support a feature called
"subclass forwarding" by which a specification can determine a target's type.

An example target type definition:

.. code-block:: python3

  from typing import Protocol
  from artisan import Target
  from .my_lib import Integrator

  class SolarSystem(Target):
      'An N-body simulation in 3 dimensions.'

      class Spec(Protocol):
          m: List[float]; 'Body masses, in kilograms.'
          xyz_init: List[List[float]]; 'Initial (x, y, z) positions, in meters.'
          dt: float = 86400.0; 'The timestep duration, in seconds.'
          integrator: Integrator.Spec; 'How to do all the hard math.'

      def __init__(self, spec: Spec) -> None:
          self.bodies = list(zip(spec.m, spec.xyz_init))
          self.integrator = Integrator(spec.integrator)
          self.dt = spec.dt

      def update(self) -> None:
          'Advance one timestep into the future.'
          # Hold on tight...
          #
          #     ☄️          ⬅ 🪐
          #    ⬇
          #           🌞
          #                  ⬆
          #    🌎 ➡         🐄
          #



Target specifications
---------------------

A target constructor must accept a specification object as its first non-`self`
argument. Specifications are namespace-like objects (objects with a `__dict__`
attribute) containing integers, floating-point numbers, strings, `True`,
`False`, `None`, `pathlib.Path` objects, :ref:`artifacts<Working with
artifacts>`, sequences of allowed values, and/or namespace-like collections of
allowed values.

Targets can be constructed from JSON-encodable objects using `artisan.build`,
which deeply converts dictionaries to namespaces and strings in the form
"@/<path>" to artifacts, if the path corresponds to a directory, or `Path`
objects, otherwise. Paths are constructed relative to the :ref:`active context
<Working with contexts>`'s root artifact directory, which is the current working
directory by default.

.. code-block:: python3

  solar_system = artisan.build(SolarSystem, {
      'integrator': {'method': 'Euler', 'precision': 'float64'},
      'xyz_init': [[1e9, 1e9, 2e9], [3e9, 5e9, 8e9]],
      'm': [2.7182e8, 3.1415e9],
      'dt': 525600})



Specification types
-------------------

`Target` types can define an inner `Spec` class to indicate the specification
object's expected type. Defining this class as a `protocol
<https://docs.python.org/3/library/typing.html#typing.Protocol>`_ indicates to
readers and type checkers that the specification's precise type is not
important, so long as it has the expected structure. If `Spec` is not defined
explicitly, it will be defined implicitly as a protocol with no required
attributes.

Public, non-callable attributes of `Spec` will be used to fill in missing
specification attributes:

.. code-block:: python3

  from types import SimpleNamespace as Ns

  solar_system = SolarSystem(Ns(
      integrator = Ns(method='Euler', precision='float64'),
      xyz_init = [[1e9, 1e9, 2e9], [3e9, 5e9, 8e9]],
      m = [2.7182e8, 3.1415e9]))

  solar_system.dt # => 86400.0 (taken from `SolarSystem.Spec`)

Inner `Spec` classes also help Artisan generate more useful APIs and user
interfaces, and help static analysis tools like `MyPy <http://mypy-lang.org/>`_
and `Jedi <https://jedi.readthedocs.io/en/latest/>`_ detect errors and provide
suggestions.



Subclass forwarding
-------------------

If a target is constructed with a specification that has a `type` attribute,
that attribute is dereferenced in the active context's target-type scope and an
instance of the resulting type is returned. The default target-type scope
contains every `Target` subclass defined outside of the Artisan library, keyed
by its name, if its name is unique, and "<name> (<module name>)", otherwise.

.. code-block:: python3

  class Animal(Target):
      'Like a plant, but faster.'

  class Bat(Animal):
      class Spec(Protocol):
          wingspan: float; 'In inches.'
          has_vampirism: bool = False

  class Capybara(Animal):
      class Spec(Protocol):
          tooth_length: float; 'Also in inches.'

  Animal(Ns(type='Bat', wingspan=8.0)) # constructs a bat
  Animal(Ns(type='Capybara', tooth_length=2.3)) # constructs a capybara

Custom scopes can be activated using the context API:

.. code-block:: python3

  with artisan.using_context(scope={'FlutterMouse': Bat, 'WaterPig': Capybara}):
      Animal(Ns(type='FlutterMouse', wingspan=8.0)) # constructs a bat

And types can be specified directly as well:

.. code-block:: python3

  Animal(Ns(type=Capybara, tooth_length=2.3)) # constructs a capybara

Instantiating targets with `artisan.build` can help avoid confusing
type-checkers when using subclass forwarding with abstract types:

.. code-block:: python3

  from abc import abstractmethod

  class TalkingAnimal(Target):
      @abstractmethod
      def talk(self) -> str: ...

  class TalkingCat(TalkingAnimal):
      def talk(self) -> str:
          return 'I can has cheezburger, but I chooz not to.'

  cat = artisan.build(TalkingAnimal, {'type': 'TalkingCat'})
  type(cat) # => <class 'TalkingCat'>
