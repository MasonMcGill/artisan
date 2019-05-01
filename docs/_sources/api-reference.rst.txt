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
  push_conf
  pop_conf
  using_conf
  get_conf
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
.. autofunction:: push_conf(conf: Optional[Conf] = None, **updates) -> None
.. autofunction:: pop_conf() -> Conf
.. autofunction:: using_conf(conf: Optional[Conf] = None, **updates) -> Iterator[None]
.. autofunction:: get_conf() -> Conf

.. autofunction:: serve
