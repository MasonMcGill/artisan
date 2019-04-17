Related projects
================

- `Luigi <https://luigi.readthedocs.io/en/stable/>`_ excels at to managing
  large, complex graphs of commands, possibly distributed across multiple
  machines. From the developers: *"Luigi is a Python module that helps you build
  complex pipelines of batch jobs. It handles dependency resolution, workflow
  management, visualization etc. It also comes with Hadoop support built in."*

- `Sacred <https://pypi.org/project/sacred/>`_ is designed to solve the same
  kinds of problems that Artisan attempts to address, though it's generally more
  oriented towards writing scripts than writing typed APIs. It also includes
  features to manage random seeds. From the developers: *"Sacred is a tool to
  help you configure, organize, log and reproduce experiments."*

- `ExDir <https://exdir.readthedocs.io/en/latest/>`_ is a directory structure
  for data generated from experimental pipelines. Artisan emits similarly
  structured directories, but relaxes the requirement that non-array files be
  sequestered in a *"raw"* directory.

- `GNU Make <https://www.gnu.org/software/make/>`_. Sometimes it's best to just
  keep things simple : )