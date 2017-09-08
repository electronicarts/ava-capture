var webpack = require('webpack');
var webpackMerge = require('webpack-merge');
var ExtractTextPlugin = require('extract-text-webpack-plugin');
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

  output: {
    path: helpers.root('dist-dev'),
    publicPath: '/static/d/',
    filename: '[name].js',
    chunkFilename: '[id].chunk.js'
  },

  plugins: [
    new ExtractTextPlugin('[name].css'),
    new webpack.LoaderOptionsPlugin({
      options: {
        metadata: metadata
      }
    }),
    new HtmlWebpackPlugin({
      template: 'src/index.html',
      metadata: metadata,
    })
  ],

  devServer: {
    historyApiFallback: true,
    stats: 'minimal'
  }
});
