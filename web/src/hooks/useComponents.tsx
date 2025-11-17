import {
  alertManagerComponent,
  configServerComponent,
  grafanaComponent,
  obagentComponent,
  obproxyComponent,
  prometheusComponent,
} from '@/pages/constants';
import { intl } from '@/utils/intl';
import { useModel } from '@umijs/max';

/**
 * @param extra 是否携带 Prometheus grafana
 */
export const useComponents = (extra?: boolean, standAlone?: boolean) => {
  const {
    OBAGENT_DOCS,
    OBPROXY_DOCS,
    OBCONFIGSERVER_DOCS,
    DOCS_PROMETHEUS,
    DOCS_GRAFANA,
  } = useModel('global');
  let params = [
    ...(!standAlone
      ? [
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
      ]
      : []),

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

    ...(!standAlone
      ? [
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
              name: 'OBConfigServer',
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
      ]
      : []),
  ];

  if (extra) {
    params = [
      ...params,
      {
        group: '工具',
        key: 'prometheusTool',
        onlyAll: true,
        content: [
          {
            key: prometheusComponent,
            name: 'Prometheus',
            onlyAll: true,
            desc: intl.formatMessage({
              id: 'OBD.pages.Obdeploy.InstallConfig.ISDM1245',
              defaultMessage:
                '是一套开源的监控&报警&时间序列数据库的组合，基本原理是通过HTTP 协议周期性抓取被监控组件的状态。',
            }),
            doc: DOCS_PROMETHEUS,
          },
        ],
      },
      {
        group: '工具',
        key: 'grafanaTool',
        onlyAll: true,
        content: [
          {
            key: grafanaComponent,
            name: 'Grafana',
            onlyAll: true,
            desc: intl.formatMessage({
              id: 'OBD.pages.Obdeploy.InstallConfig.ISDM1246',
              defaultMessage:
                '是一款采用 go 语言编写的开源应用，主要用于大规模指标数据的可视化展现，是网络架构和应用分析中最流行的时序数据展示工具。',
            }),
            doc: DOCS_GRAFANA,
          },
        ],
      },
      {
        group: '工具',
        key: 'alertManagerTool',
        onlyAll: true,
        content: [
          {
            key: alertManagerComponent,
            name: 'AlertManager',
            onlyAll: true,
            desc: intl.formatMessage({
              id: 'OBD.pages.Obdeploy.InstallConfig.AlertManagerDescription',
              defaultMessage:
                '是一个开源的告警管理器，用于处理来自 Prometheus 等监控系统的告警，并提供告警的去重、分组、路由和静默等功能。',
            }),
            doc: DOCS_PROMETHEUS,
          },
        ],
      },
    ];
  }
  return params;
};
