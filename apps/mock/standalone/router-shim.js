// The app uses BrowserRouter, which needs a server that answers every path. A single file opened from disk has none, so in this build
// BrowserRouter is HashRouter (addresses look like file.html#/insights). Everything else is the real react-router-dom.
export * from 'react-router-dom-real'
export { HashRouter as BrowserRouter } from 'react-router-dom-real'
