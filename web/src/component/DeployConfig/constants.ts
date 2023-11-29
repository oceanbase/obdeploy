import { intl } from '@/utils/intl';

export type VersionInfoType = {
  version: string;
  md5: string;
  release: string;
  versionType: string;
  value?: string;
};

export type TableDataType = {
  name: string;
  versionInfo: VersionInfoType[];
  componentInfo: ComponentMetaType;
  key:string
};

export type ClusterNameType = {
  label: string;
  value: string;
};

export type ComponentMetaType = { name: string; desc: string; url: string ,key:string};

export const OCEANBASE = 'oceanbase';
export const OBPROXY = 'obproxy';
export const OCP = 'ocp-server';
export const OCEANBASE_META:ComponentMetaType = {
  key:OCEANBASE,
  name:'OceanBase',
  desc: intl.formatMessage({
    id: 'OBD.component.DeployConfig.FinancialLevelDistributedDatabasesAre',
    defaultMessage:
      '金融级分布式数据库，具备数据强一致，高扩展、高性价比稳定可靠等特征',
  }),
  url: 'https://www.oceanbase.com/docs/oceanbase-database-cn',
}

export const OCP_META:ComponentMetaType = {
  key:OCP,
  name:'OCP',
  desc: intl.formatMessage({
    id: 'OBD.component.DeployConfig.EnterpriseLevelDataManagementPlatform',
    defaultMessage:
      '以 OceanBase 为核心的企业级数据管理平台，实现 OceanBase 全生命周期运维管理',
  }),
  url: 'https://www.oceanbase.com/docs/common-oceanbase-database-cn-10000000001577895',
}

export const OBPROXY_META:ComponentMetaType = {
  key:OBPROXY,
  name:'OBProxy',
  desc: intl.formatMessage({
    id: 'OBD.component.DeployConfig.OceanbaseADedicatedDatabaseProxy',
    defaultMessage:
      'OceanBase 数据库专用代理服务器，可将用户的 SQL 请求转发至最佳目标 OBServer',
  }),
  url: 'https://www.oceanbase.com/docs/odp-doc-cn',
}
export const CompoentsInfo:ComponentMetaType[] = [OCP_META,OCEANBASE_META,OBPROXY_META]


export const OCPComponent:TableDataType = {
    key:OCP,
    name:'OCP',
    versionInfo:[],
    componentInfo:OCP_META,
}

export const OBComponent:TableDataType = {
    key:OCEANBASE,
    name:'OceanBase',
    versionInfo:[],
    componentInfo:OCEANBASE_META,
}

export const OBProxyComponent:TableDataType = {
    key:OBPROXY,
    name:'OBProxy',
    versionInfo:[],
    componentInfo:OBPROXY_META,
}