Artisan is a [literate](https://en.wikipedia.org/wiki/Literate_programming) build system for explainable science. It lets you write code like this

```py
class SineWave(artisan.Artifact):
    ''' A sampled sine wave '''

    class Conf:
        f: float; 'Frequency'
        φ: float; 'Phase shift'

    ''' Computes sin(2πf⋅t + φ) for t ∈ [0, 1), sampled
    at 44.1kHz

    **Entries:**
    - t (float[44100]): Timepoints sampled ∈ [0, 1)
    - x (float[44100]): Function values at those timepoints '''

    def build(self, c: Conf) -> None:
        self.t = np.linspace(0, 1, 44100)
        self.x = np.sin(2 * np.pi * c.f * self.t + c.φ)

SineWave(f=10, φ=0) # Generates "SineWave_0000/"
SineWave(f=20, φ=0) # Generates "SineWave_0001/"
SineWave(f=10, φ=0) # Uses the existing "SineWave_0000/"
```

to generate file trees like this

```sh
├── _meta.yaml
├── SineWave_0000/
│   ├── _meta.yaml
│   ├── t.h5
│   └── x.h5
└── SineWave_0001/
    ├── _meta.yaml
    ├── t.h5
    └── x.h5
```

that can be viewed as highly customizable[^1], live-updated, interactive documents like this

*-- artisan-ui screenshot (explorer next to glossary) --*


## Features

- Users can define *artifact types*, that correspond to operations that produce a directory in the filesystem.
- Artifact instantiation that builds artifacts only when necessary.
- Concurrency-friendly array storage, via HDF5-SWMR.
- Graceful handling of files it doesn't know how to decode.
- Automatic metadata storage, including each artifact's specification & build status, as well as the global schema that defines and documents the universe of artifacts that can be created.
- Automatic conversion of `Conf` classes into JSON-Schemas
- REST API generation.


## Motivation

*-- problems it's trying to solve --*

- Artisan as a package manager for computational experiment results. Artifacts can be related in 2 ways:
    - Composition
    - Variation (including versioning)
- Artisan as an MVC framework for scientific exploration:
    - The "controller" is the user requesting certain artifacts to be built, by sending their specifications.
    - The views can be views written as Python functions using `artisan.watch` (coming soon), [React](https://reactjs.org) components using `artisan-ui`, or however best suits your needs.


## Topics

- Defining artifact types.
    - Defining a configuration schema.
    - Writing a `build` method.
    - Using in-memory components.
- Instantiating artifacts.
- Inspecting artifacts with `artisan-ui`.


[^1]: See [artisan-ui](TODO_insert_url).







It makes

CommandGraph is a small set of complimentary tools for exploratory computational research. It provides functionality to simplify the following tasks:

- Routing, validating, and storing command configurations
- Keeping track of command states and executing command dependencies when necessary
- Storing and accessing command outputs
- Generating command-line and web-based user interfaces

The full documentation is available [here](https://masonmcgill.github.io/cmdgraph/).

For the most up-to-date version, install from GitHub:

```
> pip install --upgrade https://github.com/MasonMcGill/cmdgraph/tarball/master
```
