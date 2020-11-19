API reference
=============

.. currentmodule:: artisan


Overview
--------

**Targets**

.. autosummary::
  :nosignatures:

  Target
  Namespace
  build

**Artifacts**

.. autosummary::
  :nosignatures:

  Artifact
  DynamicArtifact
  ProxyArtifactField
  recover

**Context management**

.. autosummary::
  :nosignatures:

  Context
  get_context
  push_context
  pop_context
  using_context

**Schema generation**

.. autosummary::
  :nosignatures:

  get_spec_schema
  get_spec_list_schema
  get_spec_dict_schema

**Interface generation**

.. autosummary::
  :nosignatures:

  API

.. WebUI
.. default_asset_builders
.. asset_builder

**Readers and writers**

.. autosummary::
  :nosignatures:

  PersistentList
  PersistentArray
  read_text_file
  read_json_file
  read_numpy_file
  read_cbor_file
  read_opaque_file
  write_object_as_cbor
  write_path



Targets
-------

.. autoclass:: Target(spec: Target.Spec)

  .. class:: Spec

    A protocol denoting valid specifications.

.. autoclass:: Namespace(*args: object, **kwargs: object)

.. autofunction:: build



Artifacts
---------

.. autoclass:: Artifact(spec: Artifact.Spec)

  .. class:: Spec

    A protocol denoting valid specifications.

  .. automethod:: __dir__
  .. automethod:: __getattr__
  .. automethod:: __setattr__
  .. automethod:: __delattr__
  .. automethod:: __fspath__
  .. automethod:: __truediv__(entry_name: str) -> Path

.. autoclass:: DynamicArtifact(spec: DynamicArtifact.Spec)

  .. class:: Spec

    A protocol denoting valid specifications.

  .. automethod:: __len__
  .. automethod:: __iter__
  .. automethod:: __contains__
  .. automethod:: __getitem__
  .. automethod:: __setitem__
  .. automethod:: __delitem__

.. autoclass:: ProxyArtifactField(root: Artifact, *keys: str)

  .. method:: __getattr__(key: str) -> ProxyArtifactField
  .. method:: __setattr__(key: str, value: object) -> None
  .. method:: __delattr__(key: str) -> None
  .. automethod:: append
  .. automethod:: extend

.. autofunction:: recover(cls: Type[SomeArtifact], path: os.PathLike | str, mode: str = 'read-sync') -> SomeArtifact



Context management
------------------

.. autoclass:: Context(*, root=None, scope=None, builder=None)

.. autofunction:: get_context() -> Context
.. autofunction:: push_context(context=None, *, root=None, scope=None, builder=None)
.. autofunction:: pop_context
.. autofunction:: using_context(context=None, *, root=None, scope=None, builder=None)



Schema generation
-----------------

.. autofunction:: get_spec_schema
.. autofunction:: get_spec_list_schema
.. autofunction:: get_spec_dict_schema



Interface generation
--------------------

.. autoclass:: API(*, permissions=None, ui=None, root=None, scope=None, builder=None)

  .. automethod:: serve



Readers and writers
-------------------

.. autoclass:: PersistentList(file_: io.BufferedRandom, length: int)

  .. automethod:: append
  .. automethod:: extend

.. autoclass:: PersistentArray(filename, dtype='uint8', mode='r+', offset=0, shape=None, order='C')

  .. automethod:: append
  .. automethod:: extend

.. autofunction:: read_text_file(path: Annotated[Path, ''.txt'']) -> str
.. autofunction:: read_json_file(path: Annotated[Path, ''.json'']) -> Any
.. autofunction:: read_numpy_file(path: Annotated[Path, ''.npy'', ''.npz'']) -> Any
.. autofunction:: read_cbor_file(path: Annotated[Path, ''.cbor'']) -> Any
.. autofunction:: read_opaque_file(path: Path) -> Path
.. autofunction:: write_object_as_cbor(path: Path, val: object) -> str
.. autofunction:: write_path(path: Path, val: Path) -> str
