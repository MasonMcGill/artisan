Artisan
=======

Artisan is a build system for explainable science. It lets you write code like
this

.. code-block:: python3

  class SineWave(Artifact):
      ''' A sampled sine wave '''

      class Conf:
          f: float; 'Frequency'
          φ: float = 0; 'Phase shift'

      #-- Fields --#
      t: ArrayFile; 'Timestamps, in seconds'
      x: ArrayFile; 'Function values at those timestamps'

      ''' Computes sin(2πf⋅t + φ) for t ∈ [0, 1s), sampled at 44.1kHz. '''

      def build(self, c: Conf) -> None:
          self.t = np.linspace(0, 1, 44100)
          self.x = np.sin(2 * np.pi * c.f * self.t + c.φ)

  SineWave(f=10, φ=0) # Generates "SineWave_0000/"
  SineWave(f=20, φ=0) # Generates "SineWave_0001/"
  SineWave(f=10, φ=0) # Uses the existing "SineWave_0000/"

to generate file trees like this

.. code-block:: sh

  ├── SineWave_0000/
  │   ├── _meta.yaml
  │   ├── t.h5
  │   └── x.h5
  └── SineWave_0001/
      ├── _meta.yaml
      ├── t.h5
      └── x.h5

that can be viewed as customizable, live-updated, interactive documents like
this

*-- artisan-ui screenshot --*

Artisan acts as a "package manager" for the results of configurable operations
(artifacts), keeping track of dependencies, versioning artifacts based on their
configuration, and allowing authors to associate documentation and interactive
visualizations with each artifact type.


Guide contents
--------------

- `Working with configurable objects <working-with-configurable-objects.html>`_
  explains how to use the abstract `Configurable` class, which provides features
  to types whose constructors accept a JSON-like configuration argument.

- `Working with artifacts <working-with-artifacts.html>`_ explains how to use and
  define artifacts, configurable objects corresponding to file trees.

- `Generating a REST API <generating-a-rest-api.html>`_ explains how to create
  and query artifacts over HTTP.

- `Generating an HTML UI <generating-an-html-ui.html>`_ explains how to create
  and explore artifacts using a web browser, and how to define custom artifact
  views.

- The `API reference <api-reference.html>`_ contains comprehensive class and
  function documentation.

- The `related projects <related-projects.html>`_ section describes tools that
  (potential) users of Artisan might find interesting.


Installation
------------

.. code-block:: shell

  > pip install artisan-builder


Contributing
------------

`Please do! <https://github.com/MasonMcGill/artisan>`_


.. toctree::
  :hidden:

  working-with-configurable-objects
  working-with-artifacts
  generating-a-rest-api
  generating-an-html-ui
  api-reference
  related-projects
