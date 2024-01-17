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
  key: string;
};

export type ClusterNameType = {
  label: string;
  value: string;
};

export type ComponentMetaType = {
  name: string;
  desc: string;
  url: string;
  key: string;
};

export function getCompoents(
  OBD_DOCS: string,
  OCP_DOCS: string,
  OBPROXY_DOCS: string,
) {
  const OCEANBASE = 'oceanbase';
  const OBPROXY = 'obproxy';
  const OCP = 'ocp-server';

  const OCEANBASE_META: ComponentMetaType = {
    key: OCEANBASE,
    name: 'OceanBase',
    desc: intl.formatMessage({
      id: 'OBD.component.DeployConfig.FinancialLevelDistributedDatabasesAre',
      defaultMessage:
        '金融级分布式数据库，具备数据强一致，高扩展、高性价比稳定可靠等特征',
    }),
    url: OBD_DOCS,
  };

  const OCP_META: ComponentMetaType = {
    key: OCP,
    name: 'OCP',
    desc: intl.formatMessage({
      id: 'OBD.component.DeployConfig.EnterpriseLevelDataManagementPlatform',
      defaultMessage:
        '以 OceanBase 为核心的企业级数据管理平台，实现 OceanBase 全生命周期运维管理',
    }),
    url: OCP_DOCS,
  };

  const OBPROXY_META: ComponentMetaType = {
    key: OBPROXY,
    name: 'OBProxy',
    desc: intl.formatMessage({
      id: 'OBD.component.DeployConfig.OceanbaseADedicatedDatabaseProxy',
      defaultMessage:
        'OceanBase 数据库专用代理服务器，可将用户的 SQL 请求转发至最佳目标 OBServer',
    }),
    url: OBPROXY_DOCS,
  };
  const CompoentsInfo: ComponentMetaType[] = [
    OCP_META,
    OCEANBASE_META,
    OBPROXY_META,
  ];

  const OCPComponent: TableDataType = {
    key: OCP,
    name: 'OCP',
    versionInfo: [],
    componentInfo: OCP_META,
  };

  const OBComponent: TableDataType = {
    key: OCEANBASE,
    name: 'OceanBase',
    versionInfo: [],
    componentInfo: OCEANBASE_META,
  };

  const OBProxyComponent: TableDataType = {
    key: OBPROXY,
    name: 'OBProxy',
    versionInfo: [],
    componentInfo: OBPROXY_META,
  };
  return {
    OCEANBASE,
    OBPROXY,
    OCP,
    OCEANBASE_META,
    OCP_META,
    OBPROXY_META,
    CompoentsInfo,
    OCPComponent,
    OBComponent,
    OBProxyComponent,
  };
}
