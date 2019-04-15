API reference
=============

.. currentmodule:: artisan


Summary
-------

.. autosummary::
  :nosignatures:

  Configurable
  Artifact
  ArrayFile
  EncodedFile
  Conf
  conf_stack
  serve


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

.. autoclass:: Conf

.. autoclass:: ConfStack

  .. automethod:: push(conf: Optional[Conf] = None, **updates) -> None
  .. automethod:: pop() -> Conf
  .. automethod:: using(conf: Optional[Conf] = None, **updates) -> Iterator[None]
  .. automethod:: get() -> Conf

.. autofunction:: serve
