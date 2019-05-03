var webpack = require('webpack');
var webpackMerge = require('webpack-merge');
var HtmlWebpackPlugin = require('html-webpack-plugin');
var commonConfig = require('./webpack.common.js');
var helpers = require('./helpers');

const ENV = process.env.NODE_ENV = process.env.ENV = 'development';

var metadata = {
  title: '(DEV) AVA Capture - SEED - Electronic Arts',
  baseUrl: '/static/d/index.html',
  host: '127.0.0.1',
  port: 3000,
  ENV: ENV
};

module.exports = webpackMerge(commonConfig, {
  devtool: 'cheap-module-eval-source-map',

  optimization: {
    minimize: false
  },

  output: {
    path: helpers.root('dist-dev'),
    publicPath: '/static/d/',
    filename: '[name].js',
    chunkFilename: '[id].chunk.js'
  },

  plugins: [
    new webpack.DefinePlugin({
      'process.env': {
        'ENV': JSON.stringify(ENV),

        // Get these variables from the environment variables
        'GIT_VERSION': JSON.stringify(process.env.GIT_VERSION),
        'AUTH_URL': JSON.stringify(process.env.AUTH_URL),
        'AUTH_CLIENT_ID': JSON.stringify(process.env.AUTH_CLIENT_ID),
        'AUTH_REDIRECT_URI': JSON.stringify(process.env.AUTH_REDIRECT_URI),
      }
    }),
    new webpack.LoaderOptionsPlugin({
      options: {
        metadata: metadata
      }
    }),
    new HtmlWebpackPlugin({
      template: 'src/index.html',
      metadata: metadata,
      ga: ''
    })
  ],

  devServer: {
    historyApiFallback: true,
    stats: 'minimal'
  }
});
