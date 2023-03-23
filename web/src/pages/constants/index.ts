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

export const componentsNameConfig = {
  [oceanbaseComponent]: {
    name: '集群',
    showComponentName: 'OceanBase DataBase',
    type: '数据库',
  },
  [obproxyComponent]: {
    name: 'OBProxy ',
    showComponentName: 'OBProxy',
    type: '代理',
  },
  [obagentComponent]: {
    name: 'OBAgent ',
    showComponentName: 'OBAgent',
    type: '工具',
  },
  [ocpexpressComponentKey]: {
    name: 'OCPExpress ',
    showComponentName: 'OCPExpress',
    type: '工具',
  },
};

export const componentsConfig = {
  [oceanbaseComponent]: {
    name: '集群',
    showComponentName: 'OceanBase DataBase',
    type: '数据库',
    componentKey: oceanbaseComponent,
  },
  [obproxyComponent]: {
    name: 'OBProxy ',
    showComponentName: 'OBProxy',
    type: '代理',
    componentKey: obproxyComponent,
  },
  [obagentComponent]: {
    name: 'OBAgent ',
    showComponentName: 'OBAgent',
    type: '工具',
    componentKey: obagentComponent,
  },
  [ocpexpressComponent]: {
    name: 'OCPExpress ',
    showComponentName: 'OCPExpress',
    type: '工具',
    componentKey: ocpexpressComponentKey,
  },
};

export const modeConfig = {
  PRODUCTION: '最大占用',
  DEMO: '最小可用',
};

export const pathReg = /^\/[0-9a-zA-Z~@%^_+=(){}\[\]:,.?/\/]+$/;

export const pathRule = {
  pattern: pathReg,
  message:
    '以 “/” 开头的绝对路径，只能包含字母、数字和特殊字符（~@%^_+=(){}[]:,./）',
};
