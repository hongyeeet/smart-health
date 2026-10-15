export default {
  locales: ['en'],
  output: 'src/i18n/locales/$LOCALE.generated.json',
  input: ['src/**/*.{ts,tsx}'],
  defaultValue: (_l, _n, _k, v) => v,
  keySeparator: '.',
  sort: true,
}
