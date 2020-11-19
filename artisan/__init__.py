'''
A lightweight experiment management library with support for gradual typing.
'''

__version__ = '0.3.0'
__author__ = 'Mason McGill'
__email__ = 'mmcgill@caltech.edu'

# The imports below are arranged such that each imported
# definition only depends on those above it.

from ._namespaces import (
    Namespace) # A `SimpleNamespace` that prints readably.

from ._cbor_io import (
    PersistentArray, # A `numpy.memmap` backed by a CBOR file.
    PersistentList, # A `list` backed by a CBOR file.
    read_cbor_file, # Read a CBOR file.
    write_object_as_cbor) # Write an object to a CBOR file.

from ._misc_io import (
    read_text_file, # Read a text file using `Path.read_text`.
    read_json_file, # Read a JSON file using `json.load`.
    read_numpy_file, # Read a NumPy array file using `numpy.load`.
    read_opaque_file, # Return the given path, unchanged.
    write_path) # Create a symbolic link.

from ._targets import (
    Target) # A user-constructable object.

from ._artifacts import (
    Artifact, # A target that acts as a typed view into a directory.
    DynamicArtifact, # An artifact with dynamically named fields.
    ProxyArtifactField, # An artifact field that does not yet exist.
    build, # Build a target based on a specification.
    recover) # Recover an existing artifact.

from ._context import (
    Context, # A collection of target-construction options.
    get_context, # Return the call stack's currently active context.
    push_context, # Replace the active context in the current call stack.
    pop_context, # Revert to the previously active context.
    using_context) # Return a context manager that activates a context.

from ._schemas import (
    get_spec_schema, # Return a JSON Schema for artifact specifications.
    get_spec_list_schema, # Return a schema for lists of artifact specs.
    get_spec_dict_schema) # Return a schema for artifact spec dictionaries.

from ._http import (
    API) # A WSGI server that provides access to an Artisan context.

__all__ = [
    'API',
    'Artifact',
    'Context',
    'DynamicArtifact',
    'Namespace',
    'PersistentArray',
    'PersistentList',
    'ProxyArtifactField',
    'Target',
    'build',
    'get_context',
    'get_spec_dict_schema',
    'get_spec_list_schema',
    'get_spec_schema',
    'pop_context',
    'push_context',
    'read_cbor_file',
    'read_json_file',
    'read_numpy_file',
    'read_opaque_file',
    'read_text_file',
    'recover',
    'using_context',
    'write_object_as_cbor',
    'write_path']

# Remove submodule names from the `__module__` attribute of all exports.
for key in __all__:
    if globals()[key].__module__.startswith(__name__):
        globals()[key].__module__ = __name__
del key
