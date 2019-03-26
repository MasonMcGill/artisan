Crafty
======

Crafty is a build system for explainable science. It helps you craft *artifacts* (directories with stuff inside) from *specifications* (JSON-like objects).

.. code-block:: python

  import crafty as cr

  class Greeting(cr.Artifact):
    ''' A friendly artifact '''

    class Conf:
      name: str; 'A long-winded pointer'

    def build(self, conf):
      self.msg = f'Hello, {conf.name}!'

  greeting = Greeting(name='Sven')
  greeting.msg  # >> 'Hello, Sven!'
  greeting.path # >> '__main__$Greeting_2019-02-02-0000'
  greeting.meta # >> {'spec': {'type': '__main__$Greeting', 'name': 'Sven'}, 'status': done}



...


.. CommandGraph
.. ============

.. CommandGraph is a small set of complimentary tools for exploratory computational research. It provides functionality to simplify the following tasks:

.. - Routing, validating, and storing command configurations
.. - Keeping track of command states and executing command dependencies when necessary
.. - Storing and accessing command outputs
.. - Generating command-line and web-based user interfaces

.. Design
.. ------

.. CommandGraph attempts to provide a minimal, coherent interface based on standard, cross-language technologies, including

.. - `YAML <http://yaml.org/>`_/`JSON <https://www.json.org/>`_ for configuration authoring
.. - `JSON-Schema <http://json-schema.org/>`_ for configuration validation
.. - `HDF5-SWMR <http://docs.h5py.org/en/latest/swmr.html>`_ for concurrency-safe array serialization, and
.. - `REST/HTTP <https://en.wikipedia.org/wiki/Representational_state_transfer>`_ for exploring command outputs.

.. It should take a few minutes to learn and a few days to rewrite in your favorite programming language.

.. Table of contents
.. -----------------

.. .. toctree::

..   01-installation
..   02-commands
..   03-records
..   04-configuration
..   05-api
..   06-related-packages
