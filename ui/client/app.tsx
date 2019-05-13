/**
 * View parameter storage/manipulation and data fetching 
 */

import cbor from 'cbor-js'
import dtype from 'dtype'
import nj from 'numjs'


//-----------------------------------------------------------------------------
// App, the interface exposed to user-defined views


export type AppParams = { host?: string, path?: string }


/**
 * An object passed to user-defined views as a prop (named "app"),
 * encapsulating the application's view parameters and capabilities.
 */
export class App {
  
  public params: AppParams
  public navigate: Function
  private cache: Cache
  private time: number

  constructor(params: AppParams, navigate: Function, cache: Cache, time: number) {
    this.params = { host: 'http://localhost:3000', path: '/' , ...params }
    this.navigate = navigate
    this.cache = cache
    this.time = time
    if (!this.params.path.endsWith('/')) {
      this.params.path = this.params.path + '/'
    }
  }

  /**
   * Navigate, merging `params` into `this.params`.
   */
  public navUpdating(params: object = {}): void {
    this.navigate({ ...this.params, ...params })
  }

  /**
   * Return the data at `paths`, or throw a promise if it is not yet ready.
   * 
   * `paths` can be a string, or an array or object with string elements.
   * Paths corresponding to array files are loaded as NumJs arrays.
   * Paths corresponding to directories are loaded as objects mirring the
   * directory structure.
   */
  public fetch(paths: any): any {    

    // `fetch(path)`
    if (typeof paths === 'string') {
      const req = this.getRequest(paths)
      if (req.status === 'failed')
        throw req.result
      if (req.result === undefined)
        throw req.promise
      return req.result
    }

    // `fetch([path0, path1, ...])`
    else if (Array.isArray(paths)) {
      const reqs = paths.map(p => this.getRequest(p))
      for (const i in reqs)
        if (reqs[i].status === 'failed')
          throw reqs[i].result
      if (reqs.some(r => r.result === undefined))
        throw Promise.all(reqs.map(r => r.promise))
      return reqs.map(r => r.result)
    }
    
    // `fetch({a: pathA, b: pathB, ...})`
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
          // @ts-ignore
          throw Promise.all(Object.values(reqs).map(r => r.promise))
        resps[k] = reqs[k].result
      }
      return resps
    }
  }

  /**
   * Convert `path` to a URL and return the corresponding request.
   */
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


//-----------------------------------------------------------------------------
// `App` convenience functions


export function tryFetch(app: App, paths: any): any {
  try { return app.fetch(paths) }
  catch (e) { if (e instanceof Promise) throw e }
}


export function fetchSchema(app: App, meta: any): any {
  const rootMeta = tryFetch(app, '/_meta')
  return meta.spec !== null && rootMeta !== undefined
    ? rootMeta.schema.definitions[meta.spec.type]
    : { description: '', outputDescriptions: {}, properties: {} }
}


export function Link({ app, target, children, ...otherProps }) {
  return (
    <a onClick={() => app.navigate({ host: app.params.host, path: target })}
       children={children} 
       {...otherProps} />
  )
}


//-----------------------------------------------------------------------------
// Data fetching


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


/**
 * A long-lived object that converts urls to requests.
 */
export class Cache {

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

  /**
   * Decode the contents of a (possibly cached) CBOR-encoded response.
   */
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


// TODO: Change `navigate` to take a URL (host/path combo), and a second
// `viewParams` argument. The URL should resolve the following tokens:
// - "." -> host/path
// - ".." -> host/parentPath
// - "~" -> host
