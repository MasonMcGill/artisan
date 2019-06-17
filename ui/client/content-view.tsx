import React from 'react'

import { tryFetch } from './app'


//-----------------------------------------------------------------------------


export default function ContentView({ app }) {
  const meta = tryFetch(app, '_meta') || {}
  if (!meta.IS_ARRAY) {
    return null
  }
  else {
    const content = app.fetch(app.params.path.slice(0, -1))
    return content.ndim === 0
      ? <pre>{content.get()}</pre>
      : <pre>{JSON.stringify(content.tolist(), null, 2)}</pre>
  }
}
