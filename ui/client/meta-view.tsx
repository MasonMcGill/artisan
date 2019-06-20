import React from 'react'

import { tryFetch } from './app'


//-----------------------------------------------------------------------------


export default function MetaView({ app }) {
  const schema = tryFetch(app, '/_meta').schema || { definitions: {} }
  const meta = tryFetch(app, '_meta') || { spec: null }
  if (meta.spec === null) return null

  return (
    <div className='aui__meta-view'>
      {render(meta.spec, 0, 0, schema)}
    </div>
  )
}


//-----------------------------------------------------------------------------


type Schema = { definitions: {} }


function render(val: any, indent: number, currCol: number, schema: Schema) {
  if (Array.isArray(val)) {
    const elements = []
    for (const e of val) {
      elements.push(<br/>)
      elements.push('\u00A0'.repeat(indent) + '- ')
      if (typeof e === 'object')
        elements.push(<br/>)
      elements.push(render(e, indent + 2, indent + 4, schema))
    }
    return <>{...elements.slice(1)}</>
  }

  else if (typeof val === 'object' && val.constructor === Object) {
    const typeSchema = schema.definitions[val.type] || {}
    const propSchemas = typeSchema.properties || {}
    const elements = []
    for (const k of Object.keys(val)) {
      const desc = (propSchemas[k] || {}).description
      elements.push(<br/>)
      elements.push('\u00A0'.repeat(indent))
      elements.push(<span className='token atrule' title={desc}>{k + ': '}</span>)
      if (typeof val[k] === 'object')
        elements.push(<br/>)
      elements.push(render(val[k], indent + 2, indent + 4 + k.length, schema))
    }
    return <>{...elements.slice(1)}</>
  }

  else if (typeof val === 'string') {
    const desc = (schema.definitions[val] || {}).description
    return desc !== undefined
      ? <span className='token symbol' title={desc}>{val}</span>
      : <span className='token string' title={desc}>{val}</span>
  }

  else if (typeof val === 'number') {
    return <span className='token number'>{val}</span>
  }

  else {
    return <span className='token boolean'>{val}</span>
  }
}
