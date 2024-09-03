import AntdMomentWebpackPlugin from '@ant-design/moment-webpack-plugin';
import { defineConfig } from 'umi';

import routes from './routes';

export default defineConfig({
  routes,
  title: 'OceanBase Deployer',
  fastRefresh: true,
  favicons: ['/assets/logo.png'],
  history: { type: 'hash' },
  extraBabelPlugins:
    process.env.NODE_ENV === 'production'
      ? ['babel-plugin-dynamic-import-node']
      : [],
  mfsu: {},
  locale: {
    default: 'zh-CN',
    antd: false,
    title: false,
  },
  // openAPI: [
  //   {
  //     requestLibPath: "import { request } from '@umijs/max'",
  //     schemaPath:`${host}/openapi.json`,
  //     projectName: 'component-change',
  //     mock: true,
  //   },
  // ],
  request: {},
  model: {},
  metas: [
    {
      'http-equiv': 'Cache-Control',
      content: 'no-cache, must-revalidate',
    },
    {
      name: 'data-bizType',
      content: 'common',
    },
    {
      name: 'data-aspm',
      content: 'a3696',
    },
  ],
  headScripts: [
    `!function(modules){function __webpack_require__(moduleId){if(installedModules[moduleId])return installedModules[moduleId].exports;var module=installedModules[moduleId]={exports:{},id:moduleId,loaded:!1};return modules[moduleId].call(module.exports,module,module.exports,__webpack_require__),module.loaded=!0,module.exports}var installedModules={};return __webpack_require__.m=modules,__webpack_require__.c=installedModules,__webpack_require__.p="",__webpack_require__(0)}([function(module,exports){"use strict";!function(){if(!window.Tracert){for(var Tracert={_isInit:!0,_readyToRun:[],_guid:function(){return"xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g,function(c){var r=16*Math.random()|0,v="x"===c?r:3&r|8;return v.toString(16)})},get:function(key){if("pageId"===key){if(window._tracert_loader_cfg=window._tracert_loader_cfg||{},window._tracert_loader_cfg.pageId)return window._tracert_loader_cfg.pageId;var metaa=document.querySelectorAll("meta[name=data-aspm]"),spma=metaa&&metaa[0].getAttribute("content"),spmb=document.body&&document.body.getAttribute("data-aspm"),pageId=spma&&spmb?spma+"."+spmb+"_"+Tracert._guid()+"_"+Date.now():"-_"+Tracert._guid()+"_"+Date.now();return window._tracert_loader_cfg.pageId=pageId,pageId}return this[key]},call:function(){var argsList,args=arguments;try{argsList=[].slice.call(args,0)}catch(ex){var argsLen=args.length;argsList=[];for(var i=0;i<argsLen;i++)argsList.push(args[i])}Tracert.addToRun(function(){Tracert.call.apply(Tracert,argsList)})},addToRun:function(_fn){var fn=_fn;"function"==typeof fn&&(fn._logTimer=new Date-0,Tracert._readyToRun.push(fn))}},fnlist=["config","logPv","info","err","click","expo","pageName","pageState","time","timeEnd","parse","checkExpo","stringify","report"],i=0;i<fnlist.length;i++){var fn=fnlist[i];!function(fn){Tracert[fn]=function(){var argsList,args=arguments;try{argsList=[].slice.call(args,0)}catch(ex){var argsLen=args.length;argsList=[];for(var i=0;i<argsLen;i++)argsList.push(args[i])}argsList.unshift(fn),Tracert.addToRun(function(){Tracert.call.apply(Tracert,argsList)})}}(fn)}window.Tracert=Tracert}}()}]);`,
    'https://gw.alipayobjects.com/as/g/component/tracert/4.4.9/index.js',
  ],
  plugins: ['./config/plugin.ts', '@umijs/max-plugin-openapi'],
  chainWebpack: (config, { env }) => {
    if (env === 'production') {
      config.optimization.delete('noEmitOnErrors');
      config.plugins.delete('optimize-css');

      // 因为删除原来适配webpack4的css压缩插件，css压缩可以用 mini-css-extract-plugin
      config.optimization.minimize(true);
      //  config.optimization.minimizer(`css-esbuildMinify`).use(CSSMinimizerWebpackPlugin);
    }
    // 添加 AntdMomentWebpackPlugin 插件
    config.plugin('antd-moment').use(AntdMomentWebpackPlugin, [
      {
        // 关闭 dayjs alias，避免 antd 以外的 dayjs 被 alias 成 moment
        disableDayjsAlias: true,
      },
    ]);
    // 静态资源的文件限制调整为 1GB，避免视频等大文件资源阻塞项目启动
    config.performance.maxAssetSize(1000000000);
    return config;
  },
});
