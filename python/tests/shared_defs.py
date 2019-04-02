import sys
sys.path.append('../artisan')

import cmdgraph as cg
import numpy as np

#------------------------------------------------------------------------------

class Signal(cg.Artifact):
    ''' A periodically sampled time-varying function '''

    sample_rate: np.ndarray; '(float) Number of samples per second'
    samples: np.ndarray; '(float[n_samples]) Successive values of the function'


class SineWave(Signal):
    ''' A sampled sine wave '''

    class Conf:
        f: float; 'Frequency'
        φ: float; 'Phase shift'
        t_end: float; 'Time of the last point to compute'
        δt: float; 'Timestep size'

    ''' Computes sin(2πf⋅t + φ) for t ∈ {0, δt, 2⋅δt, ...t_end}. '''

    def build(self, c: Conf) -> None:
        t = np.linspace(0, c.t_end, c.δt)
        self.sample_rate = 1 / c.δt
        self.samples = np.sin(2 * np.pi * c.f * t + c.φ)


class SawWave(Signal):
    ''' A sampled sawtooth wave '''

    class Conf:
        f: float; 'Frequency'
        φ: float; 'Phase shift'
        t_end: float; 'Time of the last point to compute'
        δt: float; 'Timestep size'

    ''' Computes (2f⋅t + φ) % 2 for t ∈ {0, δt, 2⋅δt, ...t_end}. '''

    def build(self, c: Conf) -> None:
        t = np.linspace(0, c.t_end, c.δt)
        self.sample_rate = 1 / c.δt
        self.samples = (2 * c.f * t + c.φ) % 2


class BoxFilteredSignal(Signal):
    ''' An existing signal, convolved with a box filter '''

    class Conf:
        src: Signal.Spec; 'Input signal'
        w_box: float; 'Filter width, in seconds'

    def build(self, c: Conf) -> None:
        src = Signal(c.src)
        box = np.ones(int(src.sample_rate * c.w_box))
        self.sample_rate = src.sample_rate
        self.samples = np.convolve(src.samples, box / len(box), 'same')


'''
Features to test:
- Global configuration:
    - Defining `scope` and `root_dir`
- Defining artifact types:
    - Docstring concatenation
    - Converting `Conf` to a JSON-Schema:
        - Basic type annotations -> `type`
        - List type annotations -> `type` & `items`
        - Following string literals -> `description`
        - Following dict literals -> other properties
        - Following (str, dict)/(dict, str) literals -> `description` & other
          properties
        - Specs -> nominal types
    - Defining `Spec`
- Instantiating artifacts:
    - Case 1: (path_given, exists)
    - Case 2: (path_given, does_not_exists)
    - Case 3: (spec_given, exists)
    - Case 4: (spec_given, does_not_exist)
    - Case 5: (path_given, spec_given, exists_and_matches)
    - Case 6: (path_given, spec_given, exists_and_does_not_match)
    - Case 7: (path_given, spec_given, does_not_exist)
    - Calling `build`, passing in `conf`
    - Calling `build` without passing in `conf`
    - `build` succeeding
    - `build` raising an error
    - Instantiating artifact subtypes
    - Checking for schema mismatches
- Reading/writing/deleting/appending to/from artifacts:
    - Arrays
    - Encoded files
    - Subartifacts
- Using artifacts as collections:
    - `__iter__`
    - `__len__`
- Saving JSON-Schemas to "_meta.yaml"
'''