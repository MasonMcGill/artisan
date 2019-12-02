Generating an HTML UI
=====================

The `WebUI` class can be used to expose the current artisan context as an HTML
app.

.. code-block:: python3

  #-- web_ui.py --#
  from artisan import Artisan, WebUI

  Artisan.push(
      root_dir = 'path/to/artifacts',
      scope = {
           # Add exported types here.
      }
  )

  wsgi_app = WebUI(
      # Scripts required by client-side views.
      scripts = [
          'https://cdn.jsdelivr.net/npm/lodash@4.17.11/lodash.min.js',
          'https://cdn.plot.ly/plotly-latest.min.js',
          'my-local-library.js'
      ],

      # Like `scripts`, but each entry generates a corresponding <link> tag.
      styles = [
          'https://cdnjs.cloudflare.com/ajax/libs/bulma/0.7.4/css/bulma.min.css',
          'dependencies/my-fork-of-artisan-ui-styles.css'      
      ],

      # Aliases by which global symbols (defined by the entries in the `scripts`
      # list) can be `import`ed. The UI's core dependencies, "react" and "numjs",
      # are bound implicitly.
      bindings = {
          'lodash': '_',
          'plotly': 'Plotly',
          'my-local-library': 'SomeIdiosyncraticGlobal'
      },

      # A custom view library, mapping path templates to visualization
      # generators. When a page corresponding to an artifact is loaded, the
      # first pair matching the artifact's path is used. Visualization generators
      # can either be functions or strings pointing to them.
      views = {
          '/FooSimulation*': 'server_lib.py:build_foo_sim_view',
          '/BarRegression*/errors': 'client-lib.js:barErrView',
          '**': other_server_lib.build_default_view
      },

      # The time between automatic data refreshes, in milliseconds.
      # `null` disables automatic data refreshing.
      refresh_interval = 5000
  )

  if __name__ == '__main__':
      wsgi_app.serve(port=8000)

Like `API`\s, `WebUI`\s can either be served directly

.. code-block:: bash

  > python3 web_ui.py # simple; doesn't require the installation of an additional package

or via a WSGI server.

.. code-block:: bash

  > gunicorn web_ui:wsgi_app # enables parallelism and hot-reloading (with the right flags)


Writing server-rendered views
-----------------------------

Server-side view generators are functions that accept two arguments: the
artifact to write into and the artifact to be viewed. If a view generator
creates a file called *index.md*, its will be rendered as the view's entry
point. Otherwise, Artisan will generate an *index.md* exposing any other files
written into the view. HTML fragment, markdown, image, video, and audio files
will be recognized.

.. code-block:: python3

  #-- server_lib.py --#
  from artisan import Artifact
  import matplotlib.pyplot as plt
  import plotly.io as pio
  from .my_lib import FooSimulation
  
  def build_foo_sim_view(view: Artifact, data: FooSimulation) -> None:
      # Write *index.md*.
      view['index.md'].write_text(
          'I made two excellent figures:\n'
          '- ![]({{viewPath}}/fig1.jpg)\n'
          '- ![]({{viewPath}}/fig2.html)'
          # `{{viewPath}}` is resolved by the client.
      )
      view['index.md'].write_text('''
          I made two excellent figures:
          - ![]({{viewPath}}/fig1.jpg)
          - ![]({{viewPath}}/fig2.html)
      ''') # `{{viewPath}}` is resolved by the client.

      # Write *fig1.jpg*, with PyPlot.
      plt.plot(data.series1)
      plt.savefig(view['fig1.jpg'])
      plt.close()

      # Write *fig2.jpg*, with Plotly.
      pio.write_html(
          fig = {'data': [{'y': data.series2}]},
          file = view['fig2.html'],
          include_plotlyjs = False
      )


Writing client-rendered views
-----------------------------

Client-rendered views can be defined as `React <https://reactjs.org/>`_
components.

.. code-block:: js

  //- client-lib.js -//
  import createPlotlyComponent from 'react-plotly.js/factory'
  const Plot = createPlotlyComponent(Plotly)

  export function barErrView({ app }) {
    return <Plot data=[{y: app.fetch('series1').unpack()}]/>
  }

Artisan supports JavaScript imports (including imports from *node_modules*),
`TypeScript <https://www.typescriptlang.org/>`_, and `JSX
<https://reactjs.org/docs/introducing-jsx.html>`_. Custom components are
rendered with an `app` property that allows them to access the web UI's state
and functionality. `app` has the following members:

.. js:attribute:: path: string

  A (possibly relative) URL pointing to the current artifact being viewed.

.. js:attribute:: params: object

  The current query parameters (which can be used to store view options).

.. js:attribute:: navigate(path: string, params: object): void

  Sets the application's path and query parameters, and rerenders.

.. js:attribute:: fetch: Function

  Returns data, if it is available. Otherwise, ensures that the data has been
  requested, and suspends rendering until it has been loaded.

  Overloads
    **fetch**\(*path: string*): Resource
      Return the resource at the given path.
    **fetch**\(*paths: string[]*): Resource[]
      Return the resources at every path in an array of paths, as an analogous
      array (`paths[i]` corresponds to `resources[i]`).
    **fetch**\(*paths: {[key: string]: string}*): {[key: string]: Resource}
      Return the resources at every path in an object, as an analogous object
      (`paths[key]` corresponds to `resources[key]`).

  Resource paths are interpreted relative to `app.path`. `ArrayFile`\s are
  returned as `NumJs <https://www.npmjs.com/package/numjs>`_ arrays,
  `EncodedFile`\s are returned as raw files, and `Artifact`\s are returned as
  they are represented in the REST API.