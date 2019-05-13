import commonjs from 'rollup-plugin-commonjs'
import replace from 'rollup-plugin-replace'
import resolve from 'rollup-plugin-node-resolve'
import sucrase from 'rollup-plugin-sucrase'

export default {
  input: 'client/index.tsx',
  external: ['react', 'react-dom', 'numjs'],
  output: {
    file: 'dist/index.js',
    format: 'iife',
    name: 'ArtisanUI',
    globals: {
      'react': 'React',
      'react-dom': 'ReactDOM',
      'numjs': 'nj'
    },
    sourcemap: true
  },
  plugins: [
    sucrase({
      transforms: ['typescript', 'jsx'],
      exclude: ['node_modules/**']
    }),
    resolve({
      extensions: ['.js', '.ts', '.tsx']
    }),
    commonjs(),
    replace({
      'process.env.NODE_ENV': '"production"'
    })
  ],
  onwarn: (warning, propagate) => {
    if (warning.code !== 'THIS_IS_UNDEFINED')
      propagate(warning)
  }
}
