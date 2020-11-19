Artisan
=======

Artisan is a lightweight experiment-management library with support for gradual
typing. It allows you to write code like this:

.. code-block:: python3

  class SineWave(artisan.Artifact):
      'sin(2πf⋅t + φ) for t ∈ [0, 1sec), sampled at 44.1kHz.'

      class Spec(Protocol):
          f: float; 'Frequency'
          φ: float = 0.0; 'Phase shift'

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

*-- artisan-ui screenshot --*

to facilitate an explorable, explainable, composable-component-based approach to
scientific, analytical, and artistic programming. Complete documentation is
available on `Read the Docs <https://artisan.readthedocs.io/en/latest/>`_.



Installation
------------

.. code-block:: shell

  > pip install artisan-builder

Artisan works with CPython and PyPy 3.6+.



Development
-----------

To install the project's dependencies:

  - Install `Python 3.6+ <https://www.python.org/downloads/>`_.
  - Install `Poetry <https://python-poetry.org/docs/#installation>`_.
  - Run `poetry install --no-root`.

To run the test suite::

  > poetry run pytest

To build the HTML documentation::

  > poetry run task build-docs

To build the HTML documentation with live-previewing::

  > poetry run task serve-docs
