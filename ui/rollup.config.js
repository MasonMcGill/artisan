import ruCommonjs from 'rollup-plugin-commonjs'
import ruJson from 'rollup-plugin-json'
import ruResolve from 'rollup-plugin-node-resolve'
import ruSucrase from 'rollup-plugin-sucrase'
import ruReplace from 'rollup-plugin-replace'

export default {
  input: 'index.tsx',
  external: [
    'react', 'react-dom', 'numjs'
  ],
  output: {
    file: 'dist/index.js',
    format: 'iife',
    name: 'ArtisanUI',
    globals: {
      'react': 'React',
      'react-dom': 'ReactDOM',
      'numjs': 'nj'
    },
    sourcemap: 'inline'
  },
  plugins: [
    ruSucrase({
      transforms: ['typescript', 'jsx'],
      exclude: ['node_modules/**']
    }),
    ruReplace({
      'process.env.NODE_ENV': '"production"'
    }),
    ruResolve(),
    ruCommonjs({
      namedExports: {
        'node_modules/lodash/lodash.js': ['mapValues']
      }
    }),
    ruJson()
  ]
}
