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

      ''' Computes sin(2πf⋅t + φ) for t ∈ [0, 1), sampled at 44.1kHz. '''

      #-- Fields --#
      x: ArrayFile; 'Timepoints sampled ∈ [0, 1)'
      t: ArrayFile; 'Function values at those timepoints'

      def build(self, c: Conf) -> None:
          self.t = np.linspace(0, 1, 44100)
          self.x = np.sin(2 * np.pi * c.f * self.t + c.φ)

  SineWave(f=10, φ=0) # Generates "SineWave_0000/"
  SineWave(f=20, φ=0) # Generates "SineWave_0001/"
  SineWave(f=10, φ=0) # Uses the existing "SineWave_0000/"

to generate file trees like this

.. code-block:: sh

  ├── _meta.yaml
  ├── SineWave_0000/
  │   ├── _meta.yaml
  │   ├── t.h5
  │   └── x.h5
  └── SineWave_0001/
      ├── _meta.yaml
      ├── t.h5
      └── x.h5

that can be viewed as highly customizable, live-updated, interactive documents
like this

*-- artisan-ui screenshot --*

Artisan acts as a "package manager" for the results of configurable operations
(artifacts), keeping track of dependencies, versioning artifacts based on their
configuration, and allowing authors to associate documentation and interactive
visualizations with each artifact type.


Features
--------

- Support for defining artifact types corresponding to file-generating
  operations
- Memoized artifact instantiation (Artifacts will only be built if they don't
  already exist.)
- A configuration validator that understands artifact type hierarchies
- Concurrency-friendly array storage, via `HDF5-SWMR
  <http://docs.h5py.org/en/stable/swmr.html>`_ (and graceful handling of
  non-array data)
- Automatic storage of metadata, including each artifact's specification and
  build status, as well a glossary (as a `JSON-Schema
  <https://json-schema.org/>`_) describing the universe of artifacts that can
  be created
- REST API generation, with support for bandwidth-efficient `CBOR
  <https://cbor.io/>`_ encoding
- Visualization via ArtisanUI, which supports rendering custom `React
  <https://reactjs.org/>`_ components (including components from `React-Vis
  <https://uber.github.io/react-vis/>`_, `React-Plotly
  <https://github.com/plotly/react-plotly.js/>`_, `Chart-Parts
  <https://microsoft.github.io/chart-parts/>`_, *etc.*)
- Full compatibility with `MyPy <http://mypy-lang.org/>`_ strong mode


Motivation
----------

Programming systems based on composing components with structured interfaces can
support powerful introspective development tools (*e.g.* `React's browser extension
<https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi?hl=en>`_,
for user interface programming, or `Max/MSP/Jitter
<https://en.wikipedia.org/wiki/Max_(software)>`_, for multimedia art creation).

Artisan is an experiment in component-oriented scientific/numerical/analytical
software. Its goal is to enable developers to define metadata-rich artifact
types in a natural, readable way, then use that metadata to automate as much as
possible, (configuration validation, file name generation, dependency
resolution, documentation generation, data presentation, thesis writing...)


Contents
--------

.. toctree::

  using-artisan
  using-artisan-ui
  api-reference
  related-projects


Contributing
------------

Please do!
