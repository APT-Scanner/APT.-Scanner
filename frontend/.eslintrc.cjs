module.exports = {
    env: {
      browser: true,
      es2021: true,
    },
    extends: ['airbnb', 'airbnb/hooks', 'eslint-config-prettier'],
    parserOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
    plugins: ['react'],
    rules: {
      'react/jsx-filename-extension': [1, { extensions: ['.js', '.jsx'] }],
      'import/prefer-default-export': 'off',
      'react/react-in-jsx-scope': 'off',
    },
  };
  