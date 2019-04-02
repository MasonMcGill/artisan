import cbor from 'cbor-js'
import dtype from 'dtype'
import * as yaml from 'js-yaml'
import { flatten, fromPairs, get, mapValues } from 'lodash'
import * as nj from 'numjs'
import * as prism from 'prismjs'
import * as React from 'react'
import { Suspense, useEffect, useState } from 'react'
import { FaDatabase, FaFile, FaFolder } from 'react-icons/fa'

import 'prismjs/components/prism-yaml'

//- View parameters and data fetching -----------------------------------------

function _unpack(res, prevResult) {
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


class Cache {
  _requests: object;

  constructor() {
    this._requests = {}
  }

  ensureRequested(url, time) {
    this._getRequest(url, time)
  }

  fetch(url, time) {
    const req = this._getRequest(url, time)
    if (req.result === undefined)
      throw req.promise
    return req.result
  }

  _getRequest(url, time) {
    // Find/create a request.
    if (!this._requests.hasOwnProperty(url))
      this._requests[url] = { status: 'unsent' }
    const req = this._requests[url]

    // Launch a fetch, if necessary.
    if (req.status === 'unsent' ||
        req.status === 'fulfilled' && req.launchTime < time) {
      req.promise = (
        window.fetch(`${url}?t_last=${req.launchTime || 0}`)
        .then(res => res.arrayBuffer())
        .then(buf => {
          req.result = _unpack(cbor.decode(buf), req.result)
          req.status = 'fulfilled'
        })
        .catch(() => {
          req.status = 'unsent'
        })
      )
      req.status = 'pending'
      req.launchTime = time
    }

    // Return the request.
    return req
  }
}


/**
 * An object passed to user-defined views as a prop (named "app"),
 * encapsulating the application's view parameters and capabilities.
 */
class App {
  host: string
  record: string
  params: object
  navigate: Function
  cache: Cache
  time: number

  constructor({ host, record, params, navigate, cache, time }) {
    this.host = host
    this.record = record
    this.params = params
    this.navigate = navigate
    this.cache = cache
    this.time = time
  }

  navUpdating(entries) {
    this.params = { ...this.params, ...entries }
    this.navigate(this.record, this.params)
  }

  fetch(paths) {
    const url = p => (
      this.host + (p[0] === '/' ? '' : this.record) + p
    )
    if (typeof paths === 'string') {
      return this.cache.fetch(url(paths), this.time)
    }
    else if (Array.isArray(paths)) {
      for (const p of paths) this.cache.ensureRequested(url(p), this.time)
      return paths.map(p => this.cache.fetch(url(p), this.time))
    }
    else if (typeof paths === 'object') {
      mapValues(paths, p => this.cache.ensureRequested(url(p), this.time))
      return mapValues(paths, p => this.cache.fetch(url(p), this.time))
    }
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
  // to-do: Allow props to change

  const [cache, _] = useState(() => new Cache())
  const [app, setApp] = useState(() => appFromURL(Date.now()))

  function appFromURL(time) {
    return new App({
      host: host,
      record: window.location.pathname,
      params: fromPairs([
        ...new URL(window.location.toString())
        .searchParams.entries()
      ]),
      navigate: (record, params) => {
        const query = '?' + new URLSearchParams(params)
        const url = window.location.origin + record + query
        if (window.location.toString() !== url) {
          window.history.pushState({}, '', url)
          setApp(appFromURL(app.time))
        }
      },
      cache: cache,
      time: time
    })
  }

  useEffect(() => {
    const listener = () => setApp(appFromURL(app.time))
    window.addEventListener('popstate', listener)
    return () => window.removeEventListener('popstate', listener)
  }, [])

  useEffect(() => {
    const timer = setInterval(
      () => setApp(appFromURL(Date.now())),
      refreshInterval
    )
    return () => clearInterval(timer)
  }, [refreshInterval])

  return (
    <Suspense fallback={<div/>}>
      <div className='cg-browser__root'>
        <TitleBar app={app}/>
        <MetaView app={app}/>
        <EntryList app={app}/>
        <CustomViews app={app} views={views}/>
      </div>
    </Suspense>
  )
}


function TitleBar({ app }) {
  return (
    <div className='cg-browser__title-bar'>
      {app.host}{app.record}
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
  const entries = app.fetch('_entry-names')
  const artifacts = entries.filter(e => e.endsWith('/'))
  const arrays = entries.filter(e => !e.endsWith('/') && !e.includes('.'))
  const files = entries.filter(e => !e.endsWith('/') && e.includes('.'))
  return (
    <div className='cg-browser__entry-list'>
      {artifacts.sort().map(e => <ArtifactLink app={app} key={e} path={e}/>)}
      {arrays.sort().map(e => <ArrayLink app={app} key={e} path={e}/>)}
      {files.sort().map(e => <FileLink app={app} key={e} path={e}/>)}
    </div>
  )
}


function ArtifactLink({ app, path }) {
  const onClick = () => app.navigate(`${app.record}${path}`)
  return (
    <div className='cg-browser__active-link' onClick={onClick}>
      <span className='cg-browser__icon'><FaFolder/></span>
      {' ' + path}
    </div>
  )
}


function ArrayLink({ app, path }) {
  return (
    <div className='cg-browser__inactive-link'>
      <span className='cg-browser__icon'><FaDatabase/></span>
      {' ' + path}
    </div>
  )
}


function FileLink({ app, path }) {
  return (
    <div className='cg-browser__inactive-link'>
      <span className='cg-browser__icon'><FaFile/></span>
      {' ' + path}
    </div>
  )
}


function CustomViews({ app, views }) {
  const type = get(app.fetch('_meta').spec, 'type', null)
  const matchingViews = flatten([get(views, type, [])])
  return <>{...matchingViews.map(V => <V app={app} />)}</>
}
