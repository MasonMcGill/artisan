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
