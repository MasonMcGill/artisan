Artisan
=======

Artisan is a lightweight experiment-management library with support for gradual
typing. It allows you to write code like this:

.. code-block:: python3

  class SineWave(artisan.Artifact):
      'sin(2πf⋅t + φ) for t ∈ [0, 1sec), sampled at 44.1kHz.'

      class Spec(Protocol):
          f: float; 'Frequency.'
          φ: float = 0.0; 'Phase shift.'

      def __init__(self, spec: Spec) -> None:
          self.t = np.linspace(0, 1, 44100)
          self.x = np.sin(2 * np.pi * spec.f * self.t + spec.φ)

to generate file trees like this:

.. code-block:: sh

  ├── SineWave_0000/
  │   ├── _meta_.json
  │   ├── t.cbor
  │   └── x.cbor
  └── SineWave_0001/
      ├── _meta_.json
      ├── t.cbor
      └── x.cbor

that can be viewed as customizable, live-updated, interactive documents like
this:

*-- artisan-ui screenshot coming soon! --*

to facilitate an explorable, explainable, composable-component-based approach to
scientific, analytical, and artistic programming.



Installation
------------

.. code-block:: shell

  > pip install artisan-builder

Artisan works with CPython and PyPy 3.6+.



Guide contents
--------------

- `Working with targets <working-with-targets.html>`_ describes how to define
  types that can be exposed via a command-line interface, REST API, or web UI.

- `Working with artifacts <working-with-artifacts.html>`_ describes how to
  define new types of artifacts—persistent, immutable targets corresponding to
  directory trees—and how artifacts can be created and inspected.

- `Working with contexts <working-with-contexts.html>`_ describes how to use the
  context API to customize target instantiation, and how to generate JSON
  Schemas describing the space of valid artifact specifications within a given
  context.

- `Generating a CLI <generating-a-cli.html>`_ describes how to make a
  command-line interface for creating artifacts.

- `Generating a REST API <generating-a-rest-api.html>`_ describes how to make
  artifacts and artifact types accessible over HTTP.

- `Generating a web UI <generating-a-web-ui.html>`_ describes how to create
  and inspect artifacts using a web browser, and how to define custom artifact
  views.

- The `API reference <api-reference.html>`_ contains comprehensive class and
  function documentation.



.. toctree::
  :hidden:

  working-with-targets
  working-with-artifacts
  working-with-contexts
  generating-a-cli
  generating-a-rest-api
  generating-a-web-ui
  api-reference
