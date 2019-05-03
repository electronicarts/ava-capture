var webpack = require('webpack');
var webpackMerge = require('webpack-merge');
var HtmlWebpackPlugin = require('html-webpack-plugin');
var CompressionPlugin = require('compression-webpack-plugin');
var commonConfig = require('./webpack.common.js');
var helpers = require('./helpers');

const ENV = process.env.NODE_ENV = process.env.ENV = 'production';

var metadata = {
  title: 'AVA Capture - SEED - Electronic Arts',
  baseUrl: '/d/index.html',
  host: '127.0.0.1',
  port: 3000,
  ENV: ENV
};

module.exports = webpackMerge(commonConfig, {

  mode: 'production',
  devtool: 'source-map',

  output: {
    path: helpers.root('dist-prod'),
    publicPath: '/d/',
    filename: '[name].[chunkhash].js',
    chunkFilename: '[id].[chunkhash].chunk.js'
  },

  plugins: [
    new webpack.NoEmitOnErrorsPlugin(),
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
      htmlLoader: {
        minimize: false // workaround for ng2
      }
    }),
    new webpack.LoaderOptionsPlugin({
      options: {
        metadata: metadata
      }
    }),
    new HtmlWebpackPlugin({
      template: 'src/index.html',
      metadata: metadata
    }),
    new CompressionPlugin()
  ]
});
