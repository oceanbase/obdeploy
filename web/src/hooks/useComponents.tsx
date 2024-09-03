import {
  configServerComponent,
  graphnaComponent,
  obagentComponent,
  obproxyComponent,
  ocpexpressComponent,
  prometheusComponent,
} from '@/pages/constants';
import { intl } from '@/utils/intl';
import { useModel } from '@umijs/max';

/**
 * @param extra 是否携带 Prometheus Graphna
 */
export const useComponents = (extra?: boolean) => {
  const {
    OCP_EXPRESS,
    OBAGENT_DOCS,
    OBPROXY_DOCS,
    OBCONFIGSERVER_DOCS,
    DOCS_PROMETHEUS,
    DOCS_GRAFANA,
  } = useModel('global');
  let params = [
    {
      group: intl.formatMessage({
        id: 'OBD.pages.components.InstallConfig.Proxy',
        defaultMessage: '代理',
      }),
      key: 'agency',
      onlyAll: true,
      content: [
        {
          key: obproxyComponent,
          name: 'OBProxy',
          onlyAll: true,
          desc: intl.formatMessage({
            id: 'OBD.pages.components.InstallConfig.ItIsAProxyServer',
            defaultMessage:
              '是 OceanBase 数据库专用的代理服务器，可以将用户 SQL 请求转发至最佳目标 OBServer 。',
          }),
          doc: OBPROXY_DOCS,
        },
      ],
    },
    {
      group: intl.formatMessage({
        id: 'OBD.pages.components.InstallConfig.Tools',
        defaultMessage: '工具',
      }),
      key: 'ocpexpressTool',
      onlyAll: true,
      content: [
        {
          key: ocpexpressComponent,
          name: 'OCP Express',
          onlyAll: true,
          desc: intl.formatMessage({
            id: 'OBD.pages.components.InstallConfig.ItIsAManagementAnd',
            defaultMessage:
              '是专为 OceanBase 设计的管控平台，可实现对集群、租户的监控管理、诊断等核心能力。',
          }),
          doc: OCP_EXPRESS,
        },
      ],
    },
    {
      group: intl.formatMessage({
        id: 'OBD.pages.components.InstallConfig.Tools',
        defaultMessage: '工具',
      }),
      key: 'obagentTool',
      onlyAll: true,
      content: [
        {
          key: obagentComponent,
          name: 'OBAgent',
          onlyAll: true,
          desc: intl.formatMessage({
            id: 'OBD.pages.components.InstallConfig.IsAMonitoringAndCollection',
            defaultMessage:
              '是一个监控采集框架。OBAgent 支持推、拉两种数据采集模式，可以满足不同的应用场景。',
          }),
          doc: OBAGENT_DOCS,
        },
      ],
    },
    {
      group: intl.formatMessage({
        id: 'OBD.pages.components.InstallConfig.Tools',
        defaultMessage: '工具',
      }),
      key: 'configServerTool',
      onlyAll: true,
      content: [
        {
          key: configServerComponent,
          name: 'obconfigserver',
          onlyAll: true,
          desc: intl.formatMessage({
            id: 'OBD.pages.Obdeploy.InstallConfig.ItIsAMetadataRegistration',
            defaultMessage:
              '是一个可提供 OceanBase 的元数据注册，存储和查询服务，主要实现 OBProxy 与 OceanBase 集群之间1到多以及多到多的访问能力。',
          }),
          doc: OBCONFIGSERVER_DOCS,
        },
      ],
    },
  ];
  if (extra) {
    params = [
      {
        group: '工具',
        key: 'prometheusTool',
        onlyAll: true,
        content: [
          {
            key: prometheusComponent,
            name: 'Prometheus',
            onlyAll: true,
            desc: '',
            doc: DOCS_PROMETHEUS,
          },
        ],
      },
      {
        group: '工具',
        key: 'graphnaTool',
        onlyAll: true,
        content: [
          {
            key: graphnaComponent,
            name: 'Graphna',
            onlyAll: true,
            desc: '',
            doc: DOCS_GRAFANA,
          },
        ],
      },
      ...params,
    ];
  }
  return params;
};
