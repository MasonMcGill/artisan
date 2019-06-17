import React from 'react'
import { FaDatabase, FaFile, FaFolder } from 'react-icons/fa'

import { App, Link, tryFetch } from './app'


//-----------------------------------------------------------------------------


export default function EntryList({ app }) {
  const entries = tryFetch(app, '_entries') || []
  return (
    <div className='aui__entry-list'>
      {...entries.map(e => e.type === 'artifact' ? ArtifactEntry(app, e) : null)}
      {...entries.map(e => e.type.endsWith('array') ? ArrayEntry(app, e) : null)}
      {...entries.map(e => e.type === 'file' ? FileEntry(app, e) : null)}
    </div>
  )
}


function ArtifactEntry(app: App, e: any) {
  return (
    <div className='aui__entry'>
      <Link app={app} target={app.params.path + e.name}>
        <FaFolder className='aui__icon'/>
        { e.nEntries === 1
          ? ` ${e.name} (1 entry)`
          : ` ${e.name} (${e.nEntries} entries)` }
      </Link>
    </div>
  )
}


function ArrayEntry(app: App, e: any) {
  const shapeString = e.shape.length == 0 ? '' : ', ' + e.shape.join(' × ')
  return (
    <div className='aui__entry'>
      {/* <Link app={app} target={''}> */}
        <FaDatabase className='aui__icon'/>
        {` ${e.name} (${e.dtype}${shapeString})`}
      {/* </Link> */}
    </div>
  )
}


function FileEntry(app: App, e: any) {
  return (
    <div className='aui__entry'>
      {/* <Link app={app} target={''}> */}
        <FaFile className='aui__icon'/>{' ' + e.name}
        {
          e.size <= 2**10 ? `(${e.size}B)` :
          e.size <= 2**20 ? `(${e.size/2**10}KB)` :
          e.size <= 2**30 ? `(${e.size/2**20}MB)` :
          `(${e.size/2**30}GB)`
        }
      {/* </Link> */}
    </div>
  )
}
