import React from 'react'

import { Link } from './app'


//-----------------------------------------------------------------------------


export default function TitleBar({ app }) {

  function selectHost() {
    const host = prompt('Hostname:', app.params.host)
    if (host) app.navigate({ host })
  }

  const pathParts = app.params.path.split('/').slice(1, -1)

  return (
    <div className='aui__title-bar'>
      <div className='aui__host-selector' onClick={selectHost}>
        {'< Select host >'}
      </div>
      <Link className='aui__breadcrumb' app={app} target='/'>
        {app.params.host}/
      </Link>
      {pathParts.map((p, i) => (
        <Link
          className='aui__breadcrumb'
          app={app}
          target={'/' + pathParts.slice(0, i + 1).join('/') + '/'}
          children={p + '/'}
          key={i}
        />
      ))}
    </div>
  )
}
