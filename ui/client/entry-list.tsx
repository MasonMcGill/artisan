import React from 'react'
import { FaDatabase, FaFile, FaFolder } from 'react-icons/fa'

import { tryFetch, Link } from './app'


//-----------------------------------------------------------------------------


export default function EntryList({ app }) {
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
        </div>
      ))}
      {...arrayNames.sort().map(n => (
        <div className='aui__entry' key={n}>
          <FaDatabase className='aui__icon'/>{' ' + n}
        </div>
      ))}
      {...fileNames.sort().map(n => (
        <div className='aui__entry' key={n}>
          <FaFile className='aui__icon'/>{' ' + n}
        </div>
      ))}
    </div>
  )
}
