Generating a CLI
================

An example command-line interface script, using `PyYAML
<https://pyyaml.org/wiki/PyYAMLDocumentation>`_ and `clize
<https://clize.readthedocs.io/en/stable/>`_:

.. code-block:: python3

  #!/usr/bin/env python3
  import json
  from pathlib import Path
  import artisan, clize, yaml
  from .my_lib import my_context

  def build(spec_dict_path: Path, key: str) -> None:
      'Build an artifact based on a spec in a YAML file.'
      spec_dict = yaml.safe_load(spec_dict_path.read_bytes())
      artifact = artisan.build(artisan.Artifact, spec_dict[key])
      print(f'Built {Path(artifact)}.')

  def write_schema(dst: Path) -> None:
      'Generate a JSON Schema describing valid inputs to `build`.'
      schema = artisan.get_spec_dict_schema()
      dst.write_text(json.dumps(schema, indent=2))
      print(f'Wrote a schema to {dst}.')

  with artisan.using_context(my_context):
      clize.run(build, write_schema)
