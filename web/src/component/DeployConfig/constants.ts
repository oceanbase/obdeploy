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
        '作为 OCP MetaDB, 建议采用多可用区（Zone）模式部署，结合负载均衡与高可用配置，确保多节点 OCP 的高可用性。',
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
  const OMS_META: ComponentMetaType = {
    key: 'oms',
    name: 'OMS',
    desc: '是 OceanBase 数据库一站式数据传输和同步的产品。是集数据迁移、实时数据同步和增量数据订阅于一体的数据传输服务。',
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
    OMS_META,
    OCP_META,
    OBPROXY_META,
    CompoentsInfo,
    OCPComponent,
    OBComponent,
    OBProxyComponent,
  };
}
