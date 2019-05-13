import globToRegExp from 'glob-to-regexp'
import React, { Suspense } from 'react'


//-----------------------------------------------------------------------------


export default function CustomViews({ app, views }) {
  const match = ([pattern, _]) => (
    globToRegExp(pattern, { globstar: true, extended: true })
    .test(app.params.path)
  )
  const [_, viewSpec] = views.find(match) || ['', []]
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


//-----------------------------------------------------------------------------


class ErrorBoundary extends React.Component {
  public state: { error: any; };

  constructor(props: object) {
    super(props)
    this.state = { error: null }
  }

  componentDidCatch(error: Error): void {
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
