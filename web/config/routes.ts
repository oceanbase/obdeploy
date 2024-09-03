export default [
  {
    path: '/',
    component: 'Layout',
    name: '系统布局',
    routes: [
      {
        path: '/',
        component: 'index',
        name: '欢迎页',
      },
      {
        path: 'obdeploy',
        component: 'Obdeploy',
        name: 'oceanbase部署',
      },
      {
        path: 'updateWelcome',
        component: 'OcpInstaller/Welcome',
        name: 'ocp升级欢迎页',
      },
      {
        path: 'update',
        component: 'OcpInstaller/Update',
        name: 'ocp升级',
        spmb: 'b71440',
      },
      {
        path: 'ocpInstaller/install',
        component: 'OcpInstaller/Install',
        name: '安装无MetaDB',
        spmb: 'b71462',
        exact: true,
      },
      {
        path: 'ocpInstaller/configuration',
        component: 'OcpInstaller/Configuration',
        name: '安装有MetaDB',
        spmb: 'b71463',
        exact: true,
      },
      {
        path: 'componentDeploy',
        component: 'ComponentDeploy/index',
        name: '安装组件',
      },
      {
        path: 'componentUninstall',
        component: 'ComponentUninstall/index',
        name: '卸载组件',
      },
      {
        path: 'quit',
        component: 'OcpInstaller/Quit',
        name: '退出安装程序',
        exact: true,
      },
      {
        path: '/guide',
        component: 'Guide',
        spmb: 'b57206',
        name: '部署向导',
      },
    ],
  },
];
