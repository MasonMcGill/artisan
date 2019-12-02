Working with artifacts
======================

Artifacts are persistent configurable objects. They can read, write, delete, and
extend

- `ArrayFile`\s (single-entry `HDF5-SWMR files
  <http://docs.h5py.org/en/stable/swmr.html>`_, exposed as `h5py.Dataset`
  objects),

- `OpaqueFile`\s (files in any other format, exposed as `pathlib.Path`\s), and

- other `Artifact`\s (subdirectories).

Artifact subclasses can define a `build` method that writes files to the
filesystem. This method is called when an artifact of that class is instantiated
and no matching directory exists.

.. code-block:: python3

  #-- A general usage example --#
  from artisan import Artifact, ArrayFile

  class BouncingBall(Artifact):
      ''' The trajectory of a ball bouncing in a vacuum '''

      class Conf:
          x_init: float; 'Initial position, in meters'
          v_init: float; 'Initial velocity in meters/second'
          δt: float = 0.001; 'Timestep duration, in seconds'
          n_ts: int = 25000; 'Number of timesteps to simulate'

      #-- Fields --#
      t: ArrayFile; 'Timestamp list (float64 × n_ts)'
      x: ArrayFile; 'Position trace (float64 × n_ts)'
      v: ArrayFile; 'Velocity trace (float64 × n_ts)'

      ''' The ball currently bounces in one dimension, but we're looking for an
      intern to add support for higher-dimensional bouncing. Please send resumes
      to jerry@contrivedexamplewarehouse.io. '''

      def build(self, c: Conf) -> None:
          self.t = [0.0]
          self.x = [c.x_init]
          self.v = [c.v_init]
          while len(self.t) < c.n_ts - 1:
              self.extend('t', [self.t[-1] + c.δt])
              self.extend('x', [self.x[-1] + c.δt * self.v[-1]])
              self.extend('v', [self.v[-1] - c.δt * 9.8 if self.x[-1] >= 0 else -self.v[-1]])

  ball = BouncingBall(x_init=15.0, v_init=10.0)
  ball.path # -> '/home/jerry/BouncingBall_0000'
  ball.t[:] # -> array([ 0.0, ...])
  ball.x[:] # -> array([15.0, ...])
  ball.v[:] # -> array([10.0, ...])


Instantiating artifacts
-----------------------

Instantiating an artifact from a configuration searches the `artifact root
directory <#configuring-the-artifact-root-directory>`_ for a matching entry,
returns that if it exists, and build a new artifact otherwise.

.. code-block:: python3

  ball_a = BouncingBall(x_init=15.0, v_init=10.0)
  ball_b = BouncingBall(x_init=15.0, v_init=10.0)
  ball_a.path == ball_b.path # -> True
  
Existing artifacts can also be loaded by their paths.

.. code-block:: python3

  BouncingBall('BouncingBall_0000')

Providing a path *and* a configuration returns a matching artifact, if it exists
at that path, and otherwise creates one.

.. code-block:: python3

  ball = BouncingBall('balls/bouncy_the_magnificent', x_init=15.0, v_init=10.0)
  ball.path # -> '/home/jerry/balls/bouncy_the_magnificent'

An error is raised if incompatible files/directories already exist at the
specified path.


Configuring the artifact root directory
---------------------------------------

By default, Artisan uses the current working directory for artifact path
generation and search. This can be configured via the `Artisan` API.

.. code-block:: python3

  with Artisan(root_dir='/tmp/lo-fi'):
      ball = BouncingBall(x_init=15.0, v_init=10.0, δt=0.3)
      ball.path # -> '/tmp/lo-fi/BouncingBall_0000'

The artifact root directory can be referenced as "@" in paths passed to artifact
constructors.

.. code-block:: python3

  with Artisan(root_dir='/home/jerry/balls'):
      ball = BouncingBall('@/high_drop', x_init=500.0, v_init=0.0)
      ball.path # -> '/home/jerry/balls/high_drop'


I/O details
-----------

Assigning any object that can be converted to a NumPy array to an attribute
creates a single-dataset HDF5 file. Subscript syntax (`artifact['key'] = value`)
is also supported.

.. code-block:: python3

  artifact.primes = [1, 2, 3, 5, 7]
  artifact.primes[:] # -> array([1, 2, 3, 5, 7])

Array fields can also be extended. `extend` implicitly creates a file if
necessary.

.. code-block:: python3
  
  artifact.extend('primes', [11, 13, 17]) # Just found some new ones!
  artifact.primes[:] # -> array([1, 2, 3, 5, 7, 11, 13, 17])

Assigning a path to a field copies the file at that path to
"{artifact.path}/{attr_name}". To support file extensions, "__" is translated to
"." in field names.

.. code-block:: python3
  
  artifact.poem__txt = Path('where-the-sidewalk-ends.txt')

Accessing an entry with "." or "__" in the name still returns a path, even if
nothing yet exists at that path.

.. code-block:: python3

  artifact.poem2__txt.write_text(
      'Help me; I am trapped\n'
      'In a haiku factory.\n'
      'Save me before they'
  )

Opaque files can also be extended, performing byte-level concatenation.

.. code-block:: python3

  artifact.extend('poem.txt', Path('the-iliad.txt'))

Assigning a mapping to a field creates a subartifact.

.. code-block:: python3

  artifact.spiciness_ratings = dict(jalapeño=[3500, 5500], habanero=[230_000])
  artifact.spiciness_ratings.jalapeño[:] # -> array([3500, 5500])
  artifact.spiciness_ratings.habanero[:] # -> array([230_000])

Extending subartifacts extends their fields.

.. code-block:: python3

  artifact.extend('spiciness_ratings', dict(jalapeño=[], habanero=[310_000]))
  artifact.spiciness_ratings.jalapeño[:] # -> array([3500, 5500])
  artifact.spiciness_ratings.habanero[:] # -> array([230_000, 310_000])

Accessing an uninitialized field without "." or "__" in the name returns an
empty artifact.

.. code-block:: python3

  artifact.nonexistent_dir # -> DynamicArtifact('...')
