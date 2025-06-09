import { intl } from '@/utils/intl';
export const commonStyle = { width: 216 };
export const TIME_REFRESH = 5000;
export const STABLE_OCP_VERSION = '421';
export const oceanbaseComponent = 'oceanbase';
export const oceanbaseCeComponent = 'oceanbase-ce';
export const oceanbaseStandaloneComponent = 'oceanbase-standalone';
export const obproxyComponent = 'obproxy';
export const obproxyCeComponent = 'obproxy-ce';
export const ocpexpressComponent = 'ocp-express';
export const ocpComponent = 'ocpserver';
export const obagentComponent = 'obagent';
export const commonInputStyle = { width: 484 };
export const commonPortStyle = { width: 230 };
export const commonServerStyle = { width: 316 };
export const configServerComponent = 'ob-configserver';
export const prometheusComponent = 'prometheus';
export const grafanaComponent = 'grafana';

export const ocpexpressComponentKey = 'ocpexpress';
export const configServerComponentKey = 'obconfigserver';
export const dashboardComponentKey = 'OB-Dashboard';

export const componentVersionTypeToComponent = {
  'oceanbase-ce': oceanbaseComponent,
  'obproxy-ce': obproxyComponent,
  'ob-configserver': configServerComponentKey,
  'ocp-express': ocpexpressComponentKey,
  grafanaComponent: grafanaComponent,
  prometheusComponent: prometheusComponent,
  'ob-dashboard': dashboardComponentKey,
};

export const onlyComponentsKeys = [
  obproxyComponent,
  ocpexpressComponentKey,
  obagentComponent,
  configServerComponentKey,
  grafanaComponent,
  prometheusComponent,
  dashboardComponentKey,
];

export const allComponentsKeys = [
  oceanbaseComponent,
  obproxyComponent,
  ocpexpressComponentKey,
  obagentComponent,
  configServerComponentKey,
  grafanaComponent,
  prometheusComponent,
  obproxyCeComponent,
  oceanbaseCeComponent,
  oceanbaseStandaloneComponent,
];

export const allComponentsName = [
  oceanbaseComponent,
  obproxyComponent,
  ocpexpressComponent,
  obagentComponent,
  configServerComponent,
  grafanaComponent,
  prometheusComponent,
  obproxyCeComponent,
  oceanbaseCeComponent,
  oceanbaseStandaloneComponent,
];

export const componentsConfig = {
  [oceanbaseComponent]: {
    name: intl.formatMessage({
      id: 'OBD.pages.constants.Cluster',
      defaultMessage: '集群',
    }),
    showComponentName: 'OceanBase DataBase',
    type: intl.formatMessage({
      id: 'OBD.pages.constants.Database',
      defaultMessage: '数据库',
    }),
    componentKey: oceanbaseComponent,
    labelName: intl.formatMessage({
      id: 'OBD.pages.constants.ClusterParameterName',
      defaultMessage: '集群参数名称',
    }),
  },
  [oceanbaseStandaloneComponent]: {
    name: oceanbaseStandaloneComponent,
    showComponentName: 'OceanBase DataBase',
    componentKey: oceanbaseStandaloneComponent,
    type: intl.formatMessage({
      id: 'OBD.pages.constants.Database',
      defaultMessage: '数据库',
    }),
    labelName: 'oceanbaseStandalone 参数名称',
  },
  [obproxyComponent]: {
    name: 'OBProxy',
    showComponentName: 'OBProxy',
    type: intl.formatMessage({
      id: 'OBD.pages.constants.Proxy',
      defaultMessage: '代理',
    }),
    componentKey: obproxyComponent,
    labelName: intl.formatMessage({
      id: 'OBD.pages.constants.ObproxyParameterName',
      defaultMessage: 'OBProxy 参数名称',
    }),
  },
  [obagentComponent]: {
    name: 'OBAgent',
    showComponentName: 'OBAgent',
    type: intl.formatMessage({
      id: 'OBD.pages.constants.Tools',
      defaultMessage: '工具',
    }),
    componentKey: obagentComponent,
    labelName: intl.formatMessage({
      id: 'OBD.pages.constants.ObagentParameterName',
      defaultMessage: 'OBAgent 参数名称',
    }),
  },
  [ocpexpressComponent]: {
    name: 'OCP Express',
    showComponentName: 'OCP Express',
    type: intl.formatMessage({
      id: 'OBD.pages.constants.Tools',
      defaultMessage: '工具',
    }),
    componentKey: ocpexpressComponentKey,
    labelName: intl.formatMessage({
      id: 'OBD.pages.constants.OcpExpressParameterName',
      defaultMessage: 'OCP Express 参数名称',
    }),
  },
  [ocpexpressComponentKey]: {
    name: 'OCP Express',
    showComponentName: 'OCP Express',
    type: intl.formatMessage({
      id: 'OBD.pages.constants.Tools',
      defaultMessage: '工具',
    }),
    componentKey: ocpexpressComponentKey,
    labelName: intl.formatMessage({
      id: 'OBD.pages.constants.OcpExpressParameterName',
      defaultMessage: 'OCP Express 参数名称',
    }),
  },
  [ocpComponent]: {
    name: 'OCP',
    showComponentName: 'OCP',
    type: intl.formatMessage({
      id: 'OBD.pages.constants.Tools',
      defaultMessage: '工具',
    }),
    componentKey: ocpexpressComponentKey,
    labelName: intl.formatMessage({
      id: 'OBD.pages.constants.OcpParameterName',
      defaultMessage: 'OCP 参数名称',
    }),
  },
  [configServerComponentKey]: {
    name: 'OBConfigserver',
    showComponentName: 'OBConfigserver',
    type: intl.formatMessage({
      id: 'OBD.pages.constants.Tools',
      defaultMessage: '工具',
    }),
    componentKey: configServerComponentKey,
    labelName: intl.formatMessage({
      id: 'OBD.pages.constants.ObConfigserverParameterName',
      defaultMessage: 'OB ConfigServer 参数名称',
    }),
  },
  [prometheusComponent]: {
    name: 'Prometheus',
    showComponentName: 'Prometheus',
    type: intl.formatMessage({
      id: 'OBD.pages.constants.Tools',
      defaultMessage: '工具',
    }),
    componentKey: prometheusComponent,
    labelName: intl.formatMessage({
      id: 'OBD.pages.constants.PrometheusParameterName',
      defaultMessage: 'Prometheus 参数名称',
    }),
  },
  [grafanaComponent]: {
    name: 'Grafana',
    showComponentName: 'Grafana',
    type: intl.formatMessage({
      id: 'OBD.pages.constants.Tools',
      defaultMessage: '工具',
    }),
    componentKey: grafanaComponent,
    labelName: intl.formatMessage({
      id: 'OBD.pages.constants.GrafanaParameterName',
      defaultMessage: 'Grafana 参数名称',
    }),
  },
  ['obshell_dashboard']: {
    name: 'obshell_dashboard',
    showComponentName: 'OB-Dashboard',
  },
};

export const modeConfig = {
  PRODUCTION: intl.formatMessage({
    id: 'OBD.pages.constants.MaximumOccupancy',
    defaultMessage: '最大占用',
  }),
  DEMO: intl.formatMessage({
    id: 'OBD.pages.constants.MinimumAvailability',
    defaultMessage: '最小可用',
  }),
};

export const pathReg = /^\/[a-zA-Z0-9\-_:@\/.]*$/;

export const pathRule = {
  pattern: pathReg,
  message: intl.formatMessage({
    id: 'OBD.pages.constants.AnAbsolutePathThatStarts.1',
    defaultMessage:
      '以 “/” 开头的绝对路径，只能包含字母、数字和特殊字符（-_:@/.）',
  }),
};
//https://www.oceanbase.com/docs/community-ocp-cn-1000000000261244
export const resourceMap = {
  metaDB: [
    {
      hosts: 10,
      cpu: 2,
      memory: 4,
    },
    {
      hosts: 50,
      cpu: 4,
      memory: 8,
    },
    {
      hosts: 100,
      cpu: 8,
      memory: 16,
    },
    {
      hosts: 200,
      cpu: 16,
      memory: 32,
    },
    {
      hosts: 400,
      cpu: 32,
      memory: 64,
    },
  ],

  monitorDB: [
    {
      hosts: 10,
      cpu: 2,
      memory: 8,
    },
    {
      hosts: 50,
      cpu: 4,
      memory: 32,
    },
    {
      hosts: 100,
      cpu: 8,
      memory: 64,
    },
    {
      hosts: 200,
      cpu: 16,
      memory: 128,
    },
    {
      hosts: 400,
      cpu: 32,
      memory: 256,
    },
  ],

  OCP: [
    {
      hosts: 10,
      cpu: 2,
      memory: 4,
    },
    {
      hosts: 50,
      cpu: 4,
      memory: 8,
    },
    {
      hosts: 100,
      cpu: 8,
      memory: 16,
    },
    {
      hosts: 200,
      cpu: 16,
      memory: 32,
    },
    {
      hosts: 400,
      cpu: 32,
      memory: 64,
    },
  ],
};
export const CONFIGSERVER_LOG_LEVEL = ['debug', 'info', 'warn', 'error'];
