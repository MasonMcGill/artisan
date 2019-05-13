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
import qs from 'query-string'
import React, { Suspense, useEffect, useState } from 'react'
import ReactDOM from 'react-dom'

import { App, Cache } from './app'
import TitleBar from './title-bar'
import MetaView from './meta-view'
import EntryList from './entry-list'
import CustomViewSet from './custom-view-set'


//-----------------------------------------------------------------------------
// Root view


type AppParams = { host?: string, path?: string }


type RootViewProps = {
  initParams?: AppParams,
  onNavigate?: (params: AppParams) => void,
  addNavigators?: (navigate: Function) => void,
  views?: Array<[string, React.Component | React.Component[]]>,
  refreshInterval?: number | null
}


function RootView(props: RootViewProps) {

  // Perform default prop substitution.
  const initParams = props.initParams || {}
  const onNavigate = props.onNavigate || (() => {})
  const addNavigators = props.addNavigators || (() => {})
  const views = props.views || []
  const refreshInterval = props.refreshInterval || 5000

  // Define state.
  const [params, setParams] = useState(initParams)  
  const [cache] = useState(() => new Cache())
  const [time, setTime] = useState(() => Date.now())

  // Define `navigate` and expose it to the instantiator.
  const navigate = (p: AppParams) => { setParams(p); onNavigate(p) }
  useEffect(() => addNavigators(navigate), [addNavigators])

  // Set up automatic refreshing.
  useEffect(() => {
    const refresh = setTimeout(() => setTime(Date.now()), refreshInterval)
    return () => clearTimeout(refresh)
  })

  // Define `app`, the childrens' interface to the Application state.
  const app = new App(params, navigate, cache, time)

  // Construct and return a component tree.
  return (
    <div className='aui__root'>
      <TitleBar app={app}/>
      <Suspense fallback={<div/>}>
        <MetaView app={app}/>
        <EntryList app={app}/>
        <CustomViewSet app={app} views={views}/>
      </Suspense>
    </div>
  )
}


//-----------------------------------------------------------------------------
// Interface for CLI-generated apps


export type Timestamp = { head?: number, body?: number }


export function render(): void {
  const props = window['Extension'] || {}
  const root = document.getElementById('__aui-root')
  ReactDOM.render(
    <RootView {...props}
      onNavigate={params => {
        const hash = `#/${qs.stringify(params)}`
        if (hash !== location.hash) {
          history.pushState(null, null, hash)
        }
      }}
      addNavigators={nav => {
        window.onhashchange = () => {
          nav(qs.parse(location.hash.slice(2)))
        }
        nav(qs.parse(location.hash.slice(2)))
      }}
    />,
    root
  )
}


export async function pollForUpdates(ts: Timestamp = {}) {
  const new_ts = await fetch('/extension/timestamps.json').then(r => r.json())
  if (new_ts.head > ts.head) location.reload()
  if (new_ts.body > ts.body) updateExtension()
  setTimeout(() => pollForUpdates(new_ts), 100)
}


function updateExtension() {
  const oldScript = document.querySelector('script[src="/extension/index.js"]')
  const newScript = document.createElement('script')
  newScript.src = '/extension/index.js'
  newScript.onload = render
  oldScript.parentNode.replaceChild(newScript, oldScript)
}
