import * as cbor from 'cbor-js'
import dtype from 'dtype'
import * as yaml from 'js-yaml'
import { flatten, get, mapValues, omit } from 'lodash'
import * as nj from 'numjs'
import * as prism from 'prismjs'
import * as qs from 'query-string'
import * as React from 'react'
import { Suspense, useEffect, useState } from 'react'
import { FaDatabase, FaFile, FaFolder, FaHome } from 'react-icons/fa'
import { BrowserRouter, Route, Link } from 'react-router-dom'

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
          req.result = Cache.unpack(cbor.decode(buf), req.result)
          req.status = 'fulfilled'
        })
        .catch(e => {
          req.status = 'failed'
          req.promise = new Promise(() => {})
          req.result = undefined
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
      if (req.result === undefined)
        throw req.promise
      return req.result
    }
    else if (Array.isArray(paths)) {
      const reqs = paths.map(p => this.getRequest(p))
      if (reqs.some(r => r.result === undefined))
        throw Promise.all(reqs.map(r => r.promise))
      return reqs.map(r => r.result)
    }
    else if (typeof paths === 'object') {
      const reqs = mapValues(paths, p => this.getRequest(p))
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

export function RootView(
  { host, refreshInterval, views }: (
    { host: string,
      refreshInterval: number,
      views: {[key: string]: React.Component | Array<React.Component>}
    }
  ))
{
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
            params.path || '/' + '?' +
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
                <CustomViews app={app} views={views}/>
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