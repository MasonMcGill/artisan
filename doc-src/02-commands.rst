Commands
========

To CommandGraph, a ``Command`` is an object that writes files to a directory, based on a configuration and/or the outputs of other commands.

Defining commands
-----------------

A minimal command with input and output looks like this:

.. code-block:: python

  import cmdgraph as cg

  class SayHello(cg.Command):
    output_path = 'greetings/{name}' # Config fields are substituted automatically
                                     # (though using this shorthand is optional).
    def run(self):
      self.output['message'] = (     # Records provide a concurrency-safe,
        f'Hello, {self.conf.name}!') # array-friendly view into the filesystem.

  SayHello(name='Sven')() # This writes "Hello, Sven!" to /greetins/Sven/message.h5,
                          # and writes metadata to /greetings/Sven/_cmd-spec.yaml
                          # and /greetings/Sven/_cmd-status.yaml.

Accessing command metadata
--------------------------

``cmd.spec`` returns a command's specification---its configuration, augmented with a field encoding its type---as a JSON-like object (an arbitrarily nested combination of `bool`, `int`, `float`, `str`, `NoneType`, `list`, and `SimpleNamespace` instances).

``cmd.status`` returns the command's execution status: *“running”*, *“done”*, *“stopped”*, or *“unbegun”*.

Executing commands
------------------

Calling a command (``cmd()``) invokes it unconditionally.

``require`` invokes the command if necessary and blocks until it has finished executing. It does nothing if the command's status is "done".

.. code-block:: python

  class WarpCatPictures(cg.Command):
    output_path = 'warped-cats'

    def run(self):
      cats = cg.require(GetCats(source='the-internet')) # `require` returns the dependent
      self.output['result'] = warp_thoroughly(cats)     # command's output record.
