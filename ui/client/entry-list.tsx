import React from 'react'
import { FaDatabase, FaFile, FaFolder } from 'react-icons/fa'

import { fetchSchema, tryFetch, Link } from './app'


//-----------------------------------------------------------------------------


export default function EntryList({ app }) {

  const meta = tryFetch(app, '_meta') || { spec: null }
  const schema = fetchSchema(app, meta)
  const comment = name => (
    schema.outputDescriptions[name] === undefined ? null : (
      <span className='aui__comment'>
        {' \u00A0—\u00A0 '}{schema.outputDescriptions[name]}
      </span>
    )
  )

  const names = tryFetch(app, '_entry-names') || []
  const artifactNames = names.filter(n => n.endsWith('/'))
  const arrayNames = names.filter(n => !n.endsWith('/') && !n.includes('.'))
  const fileNames = names.filter(n => !n.endsWith('/') && n.includes('.'))
  
  return (
    <div className='aui__entry-list'>
      {...artifactNames.sort().map(n => (
        <div className='aui__entry' key={n}>
          <Link app={app} target={app.params.path + n}>
            <FaFolder className='aui__icon'/>{' ' + n}
          </Link>
          {comment(n.slice(0, -1))}
        </div>
      ))}
      {...arrayNames.sort().map(n => (
        <div className='aui__entry' key={n}>
          <FaDatabase className='aui__icon'/>{' ' + n}
          {comment(n)}
        </div>
      ))}
      {...fileNames.sort().map(n => (
        <div className='aui__entry' key={n}>
          <FaFile className='aui__icon'/>{' ' + n}
          {comment(n)}
        </div>
      ))}
    </div>
  )
}
