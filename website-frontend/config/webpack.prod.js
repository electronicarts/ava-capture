var webpack = require('webpack');
var webpackMerge = require('webpack-merge');
var ExtractTextPlugin = require('extract-text-webpack-plugin');
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
  devtool: 'source-map',

  output: {
    path: helpers.root('dist-prod'),
    publicPath: '/d/',
    filename: '[name].[chunkhash].js',
    chunkFilename: '[id].[chunkhash].chunk.js'
  },

  plugins: [
    new webpack.NoEmitOnErrorsPlugin(),
    new webpack.optimize.UglifyJsPlugin({ // https://github.com/angular/angular/issues/10618
      mangle: {
        keep_fnames: true
      }
    }),
    new ExtractTextPlugin('[name].[hash].css'),
    new webpack.DefinePlugin({
      'process.env': {
        'ENV': JSON.stringify(ENV)
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
      metadata: metadata,
    }),
    new CompressionPlugin({
			asset: "[path].gz[query]",
			algorithm: "gzip",
			test: /\.(js|html)$/,
			threshold: 10240,
			minRatio: 0.8
    })
  ]
});
