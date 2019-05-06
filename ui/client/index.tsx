 /**
  * This module exports a single function, `render`, that renders the root view
  * with the given options.
  *
  * Conceptually, this module is split roughly into "core logic" (`Cache`,
  * `App`) and "UI" sections (`render` and the component definitions it relies
  * on).
  *
  * # Definition overview:
  *
  * - Cache: A long-lived object that converts URLs to fetched data or fetch
  *     errors, throwing a promise when no data is available to pause React's
  *     rendering. Only one is constructed during the application lifetime.
  *
  * - App: An immutable snapshot of the application's current state and gives
  *     views access to its capabilities (it's passed to them as a property
  *     during rendering).
  *
  * - render: renders a `RootView` (via `ReactDOM`) into "#__artisan-ui-root".
  */

import cbor from 'cbor-js'
import dtype from 'dtype'
import globToRegExp from 'glob-to-regexp'
import nj from 'numjs'
import qs from 'query-string'
import React, { Suspense, useEffect, useState } from 'react'
import ReactDOM from 'react-dom'
import Markdown from 'react-markdown-renderer'
import { FaDatabase, FaFile, FaFolder } from 'react-icons/fa'
import { BrowserRouter, Route, Link } from 'react-router-dom'

//- View parameters and data fetching -----------------------------------------

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
        req.status === 'fulfilled' && req.launchTime < refetchCutoff) {
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
      const reqs: { [k: string]: Request } = {}
      const resps: { [k: string]: Response } = {}
      for (const k in paths) {
        reqs[k] = this.getRequest(paths[k])
        if (reqs[k].status === 'failed')
          throw reqs[k].result
      }
      for (const k in paths) {
        if (reqs[k].result === undefined)
          throw Promise.all(Object.values(reqs).map(r => r.promise))
        resps[k] = reqs[k].result
      }
      return resps
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


function tryFetch(app: App, paths: any): any {
  try { return app.fetch(paths) }
  catch (e) { if (e instanceof Promise) throw e }
}


function fetchSchema(app: App, meta: any): any {
  const rootMeta = tryFetch(app, '/_meta')
  return meta.spec !== null && rootMeta !== undefined
    ? rootMeta.schema.definitions[meta.spec.type]
    : { description: '', outputDescriptions: {}, properties: {} }
}

//- User interface ------------------------------------------------------------

export type UIOptions = {
  host: string,
  refreshInterval: number | null,
  views: Array<[string, React.Component | React.Component[]]>
}


export function render(options: UIOptions) {
  const root = document.getElementById('__artisan-ui-root')
  ReactDOM.render(<RootView {...options}/>, root)
}


function RootView({ host, refreshInterval, views }: UIOptions) {
  const defaultHost = host || 'http://localhost:3000'
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
          const { path, host, ...viewParams } = params
          history.push(
            (params.path || '/') + '?' +
            qs.stringify(
              host === defaultHost
              ? viewParams
              : { host, ...viewParams }
            )
          )
        }
        const params = {
          host: defaultHost,
          path: location.pathname,
          ...qs.parse(location.search)
        }
        const app = new App(params, navigate, cache, time)
        return (
          <div className='aui__root'>
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
    <div className='aui__title-bar'>
      <div className='aui__host-selector' onClick={selectHost}>
        {'< Select host >'}
      </div>
      <Link className='aui__breadcrumb' to='/'>
        {app.params.host}/
      </Link>
      {pathParts.map((p, i) => (
        <Link
          className='aui__breadcrumb'
          to={'/' + pathParts.slice(0, i + 1).join('/') + '/'}
          children={p + '/'}
          key={i}
        />
      ))}
    </div>
  )
}


function MetaView({ app }) {
  const meta = tryFetch(app, '_meta') || { spec: null }
  if (meta.spec === null) return null

  const schema = fetchSchema(app, meta)
  const [descHead, ...descBody] = schema.description.trim().split('\n\n')
  const { type, ...conf } = meta.spec
  // const specText = yaml.dump(
  //   { ...meta.spec, status: meta.status },
  //   { lineWidth: 72 }
  // )

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


function EntryList({ app }) {
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
          <Link to={app.params.path + n}>
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


function CustomViews({ app, views }) {
  for (const [pattern, viewSpec] of views) {
    if (globToRegExp(pattern).test(app.params.path)) {
      const viewArray = Array.isArray(viewSpec) ? viewSpec : [viewSpec]
      return (
        <div className='aui__data-view'>
          {viewArray.map((View, i) => (
            <ErrorBoundary key={i}>
              <Suspense fallback={<div/>}>
                <View app={app}/>
                <br/>
              </Suspense>
            </ErrorBoundary>
          ))}
        </div>
      )
    }
  }
  return null
}


class ErrorBoundary extends React.Component {
  public state: { error: any; };

  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  componentDidCatch(error) {
    this.setState({ error })
  }

  render() {
    if (this.state.error !== null) {
      return <pre><code>{this.state.error.message}</code></pre>
    }
    else {
      return <>{this.props.children}</>
    }
  }
}
