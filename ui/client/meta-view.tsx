import React, { useState } from 'react'
import Markdown from 'react-markdown-renderer'

import { fetchSchema, tryFetch } from './app'


//-----------------------------------------------------------------------------


export default function MetaView({ app }) {
  const meta = tryFetch(app, '_meta') || { spec: null }
  if (meta.spec === null) return null

  const schema = fetchSchema(app, meta)
  const [descHead, ...descBody] = schema.description.trim().split('\n\n')
  const { type, ...conf } = meta.spec

  return (
    <div className='aui__meta-view'>
      <span className='token atrule'>type: </span>
      {meta.spec.type}
      <span className='aui__comment'>
        {' \u00A0—\u00A0 '}{descHead}
      </span>
      {
        Object.keys(conf).map(key => {
          const propSchema = schema.properties[key] || {}
          return (
            <div key={key}>
              <span className='token atrule'>{key}: </span> {conf[key]}
              {
                propSchema.description === undefined ? null : (
                  <span className='aui__comment'>
                    {' \u00A0—\u00A0 '}{propSchema.description}
                  </span>
                )
              }
            </div>
          )
        })
      }
      <DescBody app={app}/>
    </div>
  )
}


//-----------------------------------------------------------------------------


function DescBody({ app }) {
  const [collapsed, setCollapsed] = useState(true)

  if (collapsed) {
    return (
      <div className='aui__desc-body--collapsed'
            onClick={() => setCollapsed(false)}>
        {'< Expand description >'}
      </div>
    )
  }

  else {
    const meta = tryFetch(app, '_meta') || { spec: null }
    if (meta.spec === null) return null

    const schema = fetchSchema(app, meta)
    const [descHead, ...descBody] = schema.description.trim().split('\n\n')

    return (
      <div className="aui__desc-body"
            onClick={() => setCollapsed(true)}>
        <Markdown markdown={descBody.join('\n\n')}/>
      </div>
    )
  }
}
