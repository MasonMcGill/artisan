API reference
=============

.. currentmodule:: artisan


Summary
-------

Core types:

.. autosummary::

  Configurable
  Artifact

Artifact field types:

.. autosummary::

  ArrayFile
  EncodedFile

.. ============= ==============================================
.. `ArrayFile`   An alias for h5py.Dataset
.. `EncodedFile` An alias for pathlib.Path
.. ============= ==============================================

Global configuration:

.. autosummary::

  push
  pop
  using
  get

.. note:: This API may change slightly, or be moved to a submodule/singleton
          object in future versions.

REST API generation:

.. autosummary::

  serve


Details
-------

.. autoclass:: Configurable
  :members:
  :undoc-members:

.. autoclass:: Artifact
  :members:
  :undoc-members:

.. autofunction:: push
.. autofunction:: pop
.. autofunction:: using
.. autofunction:: get

.. autofunction:: serve
