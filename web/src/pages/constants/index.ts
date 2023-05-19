import { intl } from '@/utils/intl';
export const commonStyle = { width: 216 };
export const oceanbaseComponent = 'oceanbase';
export const obproxyComponent = 'obproxy';
export const ocpexpressComponent = 'ocp-express';
export const obagentComponent = 'obagent';

export const ocpexpressComponentKey = 'ocpexpress';

export const componentVersionTypeToComponent = {
  'oceanbase-ce': oceanbaseComponent,
  'obproxy-ce': obproxyComponent,
};

export const onlyComponentsKeys = [
  obproxyComponent,
  ocpexpressComponentKey,
  obagentComponent,
];

export const allComponentsKeys = [
  oceanbaseComponent,
  obproxyComponent,
  ocpexpressComponentKey,
  obagentComponent,
];

export const allComponentsName = [
  oceanbaseComponent,
  obproxyComponent,
  ocpexpressComponent,
  obagentComponent,
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

export const pathReg = /^\/[0-9a-zA-Z~@%^_+=(){}\[\]:,.?/\/]+$/;

export const pathRule = {
  pattern: pathReg,
  message: intl.formatMessage({
    id: 'OBD.pages.constants.AnAbsolutePathThatStarts',
    defaultMessage:
      '以 “/” 开头的绝对路径，只能包含字母、数字和特殊字符（~@%^_+=(){}[]:,./）',
  }),
};
