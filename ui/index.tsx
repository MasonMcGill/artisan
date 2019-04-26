import cbor from 'cbor-js'
import dtype from 'dtype'
import yaml from 'js-yaml'
import flatten from 'lodash/flatten'
import get from 'lodash/get'
import mapValues from 'lodash/mapValues'
import omit from 'lodash/omit'
import nj from 'numjs'
import prism from 'prismjs'
import qs from 'query-string'
import React, { Suspense, useEffect, useState } from 'react'
import ReactDOM from 'react-dom'
import { FaDatabase, FaFile, FaFolder } from 'react-icons/fa'
import { BrowserRouter, Route, Link } from 'react-router-dom'

window.Prism = prism
import 'prismjs/components/prism-yaml'

//- Internal type definitions -------------------------------------------------

type Request = {
  status: 'unsent' | 'pending' | 'fulfilled' | 'failed',
  launchTime?: number,
  promise?: Promise<void>,
  result?: any
}


type Response = {
  type: 'plain-object' | 'cached-value' | 'string-array' |
        'numeric-array' | 'artifact',
  content: any
}


type AppParams = {
  host: string,
  path: string
}

//- View parameters and data fetching -----------------------------------------

class Cache {
  private requests: { [k: string]: Request } = {}

  /**
   * Return a request corresponding to `url`, launching a refetch if the
   * resource at `url` was last fetched before `refetchCutoff`.
   */
  public getRequest(url: string, refetchCutoff: number): Request {
    // Find/create a request.
    if (this.requests[url] === undefined)
      this.requests[url] = { status: 'unsent' }
    const req = this.requests[url]

    // Launch a fetch, if necessary.
    if (req.status === 'unsent' ||
        req.status !== 'pending' && req.launchTime < refetchCutoff) {
      req.promise = (
        fetch(`${url}?t_last=${req.launchTime || 0}`)
        .then(res => res.arrayBuffer())
        .then(buf => {
          req.status = 'fulfilled'
          req.result = Cache.unpack(cbor.decode(buf), req.result)
        })
        .catch(e => {
          req.status = 'failed'
          req.result = e
        })
      )
      req.status = 'pending'
      req.launchTime = Date.now()
    }

    // Return the request.
    return req
  }

  private static unpack(res: Response, prevResult: any): any {
    switch (res.type) {
      case 'plain-object':
        return res.content
      case 'cached-value':
        return prevResult
      case 'string-array':
        return nj.array(res.content)
      case 'numeric-array':
        const offset = res.content.data.byteOffset
        const length = res.content.data.byteLength
        const buffer = res.content.data.buffer.slice(offset, offset + length)
        const array = new (dtype(res.content.dtype))(buffer)
        // @ts-ignore
        return new nj.NdArray(array, res.content.shape)
    }
  }
}


/**
 * An object passed to user-defined views as a prop (named "app"),
 * encapsulating the application's view parameters and capabilities.
 */
class App {
  public params: AppParams
  public navigate: Function
  private cache: Cache
  private time: number

  constructor(params: AppParams, navigate: Function, cache: Cache, time: number) {
    this.params = params
    this.navigate = navigate
    this.cache = cache
    this.time = time
    if (!params.path.endsWith('/')) {
      params.path = params.path + '/'
    }
  }

  public navUpdating(params: object = {}): void {
    this.navigate({ ...this.params, ...params })
  }

  public fetch(paths: any): any {
    if (typeof paths === 'string') {
      const req = this.getRequest(paths)
      if (req.status === 'failed')
        throw req.result
      if (req.result === undefined)
        throw req.promise
      return req.result
    }
    else if (Array.isArray(paths)) {
      const reqs = paths.map(p => this.getRequest(p))
      for (const i in reqs)
        if (reqs[i].status === 'failed')
          throw reqs[i].result
      if (reqs.some(r => r.result === undefined))
        throw Promise.all(reqs.map(r => r.promise))
      return reqs.map(r => r.result)
    }
    else if (typeof paths === 'object') {
      const reqs = mapValues(paths, p => this.getRequest(p))
      for (const i in reqs)
        if (reqs[i].status === 'failed')
          throw reqs[i].result
      if (Object.values(reqs).some(r => r.result === undefined))
        throw Promise.all(Object.values(reqs).map(r => r.promise))
      return mapValues(reqs, r => r.result)
    }
  }

  private getRequest(path: string): Request {
    return this.cache.getRequest(
      ( this.params.host
        + (path[0] === '/' ? '' : this.params.path)
        + path
      ),
      this.time
    )
  }
}

//- User interface ------------------------------------------------------------

function RootView(
  { host, refreshInterval, views }: (
    { host: string,
      refreshInterval: number | null,
      views: {[key: string]: React.Component | Array<React.Component>}
    }
  ))
{
  host = host || 'http://localhost:3000'
  refreshInterval = refreshInterval || 5000
  views = views || []

  const [cache, _] = useState(() => new Cache())
  const [time, setTime] = useState(() => Date.now())

  // Set up automatic refreshing.
  useEffect(() => {
    const refresh = setTimeout(() => setTime(Date.now()), refreshInterval)
    return () => clearTimeout(refresh)
  })

  return (
    <BrowserRouter>
      <Route path='/*' render={({ location, history }) => {
        function navigate(params) {
          history.push(
            (params.path || '/') + '?' +
            qs.stringify(
              params.host == host
              ? omit(params, ['path', 'host'])
              : omit(params, ['path'])
            )
          )
        }
        const params = {
          host, path: location.pathname,
          ...qs.parse(location.search)
        }
        const app = new App(params, navigate, cache, time)
        return (
          <div className='cg-browser__root'>
            <TitleBar app={app}/>
            <Suspense fallback={<div/>}>
              <MetaView app={app}/>
              <EntryList app={app}/>
              {/* <CustomViews app={app} views={views}/> */}
            </Suspense>
          </div>
        )
      }}/>
    </BrowserRouter>
  )
}


function TitleBar({ app }) {
  function selectHost() {
    const host = prompt('Hostname:', app.params.host)
    if (host) app.navigate({ host })
  }

  const pathParts = app.params.path.split('/').slice(1, -1)

  return (
    <div className='cg-browser__title-bar'>
      <div className='cg-browser__host-selector' onClick={selectHost}>
          [select host]
      </div>
      <Link className='cg-browser__breadcrumb' to='/'>
        {app.params.host}/
      </Link>
      {pathParts.map((p, i) => (
        <Link
          className='cg-browser__breadcrumb'
          to={'/' + pathParts.slice(0, i + 1).join('/') + '/'}
          children={p + '/'}
          key={i}
        />
      ))}
    </div>
  )
}


function MetaView({ app }) {
  let meta = app.fetch('_meta')
  const text = yaml.dump(
    { ...meta.spec, status: meta.status },
    { lineWidth: 72 }
  )
  return meta.spec === null ? null : (
    <div className='cg-browser__meta-view' dangerouslySetInnerHTML={{
      __html: prism.highlight(text, prism.languages.yaml, 'yaml')
    }}/>
  )
}


function EntryList({ app }) {
  const names = app.fetch('_entry-names')
  const artifactNames = names.filter(n => n.endsWith('/'))
  const arrayNames = names.filter(n => !n.endsWith('/') && !n.includes('.'))
  const fileNames = names.filter(n => !n.endsWith('/') && n.includes('.'))
  return (
    <div className='cg-browser__entry-list'>
      {...artifactNames.sort().map(n => (
        <div className='cg-browser__entry' key={n}>
          <Link to={app.params.path + n}>
            <FaFolder className='cg-browser__icon'/>{' ' + n}
          </Link>
        </div>
      ))}
      {...arrayNames.sort().map(n => (
        <div className='cg-browser__entry' key={n}>
          <FaDatabase className='cg-browser__icon'/>{' ' + n}
        </div>
      ))}
      {...fileNames.sort().map(n => (
        <div className='cg-browser__entry' key={n}>
          <FaFile className='cg-browser__icon'/>{' ' + n}
        </div>
      ))}
    </div>
  )
}


function CustomViews({ app, views }) {
  const type = get(app.fetch('_meta').spec, 'type', null)
  const matchingViews = flatten([get(views, type, [])])
  return (
    <div className='cg-browser__data-view'>
      {matchingViews.map((View, i) => (
        <Suspense key={i} fallback={<div/>}>
          <View app={app} />
        </Suspense>
      ))}
    </div>
  )
}

//- Entry point ---------------------------------------------------------------

export function render(options) {
  const root = document.getElementById('__artisan-ui-root')
  ReactDOM.render(<RootView {...options}/>, root)
}
