/**
 * Builds the CURRENT app (apps/web/src, unchanged) as ONE html file that opens by double-click, with no server: all code, styles and fonts
 * inside it, and recorded data from the real API (snapshot.json) answering the app's requests.
 * Output: apps/mock/smart-health-standalone.html. It is a design reference only; nothing in apps/web depends on it.
 *
 *   node apps/mock/standalone/capture.mjs     refresh the recorded data (needs the API running)
 *   node apps/mock/standalone/build.mjs       build the file (needs `npm install` done in apps/web)
 */
import { readFile, writeFile, rm, stat } from 'node:fs/promises'
import { dirname, resolve, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const web = resolve(here, '..', '..', 'web')
const outDir = resolve(here, '.build')
const target = resolve(here, '..', 'smart-health-standalone.html')

// the tools come from apps/web's own install, so the app is built with exactly the versions it normally uses
const load = async (rel) => import(pathToFileURL(resolve(web, 'node_modules', rel)).href)
const { build } = await load('vite/dist/node/index.js')
const react = (await load('@vitejs/plugin-react/dist/index.js')).default
const tailwind = (await load('@tailwindcss/vite/dist/index.mjs')).default

/** BrowserRouter becomes HashRouter (see router-shim.js). Only the app's own imports are redirected. */
const hashRouter = {
  name: 'hash-router',
  enforce: 'pre',
  async resolveId(source, importer, options) {
    if (source === 'react-router-dom-real') return this.resolve('react-router-dom', resolve(web, 'src', 'main.tsx'), { ...options, skipSelf: true })
    if (source === 'react-router-dom' && importer && !importer.endsWith('router-shim.js')) return resolve(here, 'router-shim.js')
    return null
  },
}

await build({
  root: web,
  configFile: false,
  logLevel: 'warn',
  base: './',
  plugins: [hashRouter, react(), tailwind()],
  resolve: { alias: { '@': resolve(web, 'src') } },
  build: {
    outDir,
    emptyOutDir: true,
    assetsInlineLimit: 100_000_000,
    cssCodeSplit: false,
    modulePreload: false,
    chunkSizeWarningLimit: 100_000,
    // the script is the entry (an html entry outside apps/web is refused); the html is put together below from index.html
    rollupOptions: { input: resolve(here, 'main.tsx'), output: { inlineDynamicImports: true, entryFileNames: 'app.js', assetFileNames: (a) => (a.names?.[0] ?? a.name ?? '').endsWith('.css') ? 'app.css' : 'assets/[name]-[hash][extname]' } },
  },
})

let html = await readFile(resolve(here, 'index.html'), 'utf8')
const css = await readFile(join(outDir, 'app.css'), 'utf8')       // fonts are already inside it as data
// "</script" inside the code would end the tag early, so it is escaped
const js = (await readFile(join(outDir, 'app.js'), 'utf8')).replace(/<\/script/gi, '<\\/script')

html = html.replace('<script type="module" src="./main.tsx"></script>', () => '')
html = html.replace('</head>', () => `<style>${css}</style>
  </head>`)
html = html.replace('</body>', () => `<script type="module">${js}</script>
  </body>`)
html = html.replace('<title>', '<!-- Smart Health: single-file copy with recorded data, a design reference. Built by apps/mock/standalone/build.mjs -->\n    <title>')

await writeFile(target, html)
await rm(outDir, { recursive: true, force: true })
console.log(`wrote ${target}  ${((await stat(target)).size / 1024 / 1024).toFixed(2)} MB`)
const leftovers = [...html.matchAll(/(?:src|href)="(\.?\/[^"]+|[a-z0-9_-]+\.[a-z]+)"/gi)].map((m) => m[1])
if (leftovers.length) console.log('still points at files:', leftovers.slice(0, 8))
