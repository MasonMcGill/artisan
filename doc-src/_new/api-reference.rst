API reference
=============

.. currentmodule:: artisan


Summary
-------

.. autosummary::
  :nosignatures:

  Configurable
  Artifact
  DynamicArtifact
  ArrayFile
  OpaqueFile
  Artisan
  API
  WebUI


Details
-------

.. autoclass:: Configurable
  :members:

.. autoclass:: Artifact

  .. automethod:: __len__
  .. automethod:: __iter__
  .. automethod:: __getitem__(key: str) -> ArrayFile|EncodedFile|Artifact
  .. automethod:: __setitem__
  .. automethod:: __delitem__
  .. automethod:: extend

.. autoclass:: Artisan

  .. automethod:: get_current
  .. automethod:: push
  .. automethod:: pop
  .. automethod:: __enter__
  .. automethod:: __exit__
  .. automethod:: __call__
  .. automethod:: serve

.. autoclass:: DynamicArtifact

.. autoclass:: API

.. autoclass:: WebUI
