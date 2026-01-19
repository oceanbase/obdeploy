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
  OMS_DOCS: string,
) {

  const OMS_META: ComponentMetaType = {
    key: 'oms',
    name: 'OMS',
    desc: intl.formatMessage({
      id: 'OBD.pages.Oms.Update.Component.DeployConfig.OmsDescription',
      defaultMessage: '是 OceanBase 数据库一站式数据传输和同步的产品。是集数据迁移、实时数据同步和增量数据订阅于一体的数据传输服务。',
    }),
    url: OMS_DOCS,
  };

  const CompoentsInfo: ComponentMetaType[] = [
    OMS_META,
  ];

  const OMSComponent: TableDataType = {
    key: 'oms',
    name: 'OMS',
    versionInfo: [],
    componentInfo: OMS_META,
  };

 
  return {
    OMS_META,
    CompoentsInfo,
    OMSComponent,
  };
}
