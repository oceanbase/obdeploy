import { changeParameterUnit } from '@/component/OCPPreCheck/helper';
import {
  CompDetailCheckInfo,
  CompNodeCheckInfo,
  DeployedCompCheckInfo,
  PathCheckInfo,
  UserCheckInfo,
} from '@/component/PreCheckComps';

import { DEFAULT_PROXY_PWD } from '@/constant';
import { getPublicKey } from '@/services/ob-deploy-web/Common';
import { createDeploymentConfig } from '@/services/ob-deploy-web/Deployments';
import { getErrorInfo, handleQuit } from '@/utils';
import { encryptPwdForConfig } from '@/utils/encrypt';
import { generateRandomPassword, isExist } from '@/utils/helper';
import { intl } from '@/utils/intl';
import useRequest from '@/utils/useRequest';
import { ProCard } from '@ant-design/pro-components';
import { Alert, Button, Col, Input, Row, Space, Table, TabsProps, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useEffect } from 'react';
import { getLocale, useModel } from '@umijs/max';
import {
  alertManagerComponent,
  allComponentsKeys,
  componentsConfig,
  componentVersionTypeToComponent,
  configServerComponent,
  configServerComponentKey,
  grafanaComponent,
  modeConfig,
  obagentComponent,
  obproxyComponent,
  oceanbaseComponent,
  oceanbaseStandaloneComponent,
  onlyComponentsKeys,
  prometheusComponent,
  seekdbComponent
} from '../constants';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;
interface ComponentsNodeConfig {
  name: string;
  servers: string[];
  key: string;
  isTooltip: boolean;
}

export const formatConfigData = (
  configData: API.DeploymentConfig,
  scenarioParam: any,
  publicKey: string,
  isSeekdb: boolean = false,
  clusterMore: boolean = true,
) => {
  const formatedConfigData = encryptPwdForConfig(configData, publicKey);
  let isOBConfig = false;
  const _configData = formatedConfigData.components || formatedConfigData;
  if (formatedConfigData.components) isOBConfig = true;

  // seekdb 模式：将 oceanbase 字段数据按后端 Seekdb 模型结构转换
  if (isSeekdb && _configData.oceanbase) {
    const {
      rpc_port,
      topology,
      parameters: obParameters,
      mode,
      appname,
      component,
      ...restOceanbase
    } = _configData.oceanbase as any;

    // 从 topology 中提取所有 IP 地址平铺到 seekdb.servers
    const servers: string[] = (topology || []).flatMap(
      (zone: any) => (zone.servers || []).map((s: any) => (typeof s === 'string' ? s : s.ip))
    );

    _configData.seekdb = {
      ...restOceanbase,
      // component 为后端必填字段，seekdb 模式下固定为 'seekdb'
      component: component,
      ...(servers.length ? { servers } : {}),
      ...(mode ? { mode } : {}),
      // seekdb 模式始终带上 parameters 字段；用户改动过的项才入内，未改动时发空数组
      parameters: (clusterMore && obParameters?.length)
        ? obParameters.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value))
        : [],
    };
    delete _configData.oceanbase;
  } else if (isSeekdb && (_configData as any).seekdb) {
    // getInfoByName 返回的配置已是 seekdb 结构，直接保留字段，仅过滤 parameters
    const seekdbData = (_configData as any).seekdb;
    const { parameters: seekdbParameters, ...restSeekdb } = seekdbData;
    (_configData as any).seekdb = {
      ...restSeekdb,
      parameters: (clusterMore && seekdbParameters?.length)
        ? seekdbParameters.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value))
        : [],
    };
  }

  Object.keys(_configData).forEach((key) => {
    const compData = (_configData as any)[key];
    if (typeof compData === 'object' && compData !== null) {
      // 安全检查：确保 parameters 存在且是数组
      if (Array.isArray(compData?.parameters)) {
        // seekdb 的 parameters 已在上方过滤并按 clusterMore 控制，只清理 isChanged 字段
        if (key === 'seekdb') {
          compData.parameters.forEach((parameter: any) => {
            delete parameter.isChanged;
          });
        } else {
          for (let i = 0; i < compData.parameters.length; i++) {
            const parameter = compData.parameters[i];
            // 筛选原则：修改过下拉框或者输入框的参数传给后端；自动分配、值为空的参数均不传给后端
            if (
              (!parameter.adaptive && !isExist(parameter.value)) ||
              parameter.adaptive ||
              !parameter.isChanged
            ) {
              compData.parameters.splice(i--, 1);
            }
            if (parameter.key === 'ocp_meta_tenant_memory_size') {
              parameter.value = changeParameterUnit(parameter).value;
            }
            delete parameter.isChanged;
          }
        }
      }
      if (key === configServerComponentKey && Array.isArray(compData?.parameters)) {
        compData.parameters.forEach((parameter: any) => {
          if (parameter.key === 'log_maxsize') {
            parameter.type = 'Integer';
            parameter.value = Number(parameter.value.split('MB')[0]);
          }
        });
      }
    }
  });
  if (scenarioParam) {
    // seekdb 模式 scenarioParam 注入到 seekdb 对象，否则注入到 oceanbase
    const targetKey = isSeekdb ? 'seekdb' : 'oceanbase';
    const targetConfig = _configData as any;
    if (!targetConfig[targetKey]) {
      targetConfig[targetKey] = {};
    }
    if (!targetConfig[targetKey].parameters) {
      targetConfig[targetKey].parameters = [];
    }
    targetConfig[targetKey].parameters = [
      scenarioParam,
      ...targetConfig[targetKey].parameters,
    ];
  }
  if (isOBConfig) {
    return {
      ...formatedConfigData,
      components: _configData,
    };
  }
  return _configData;
};

export default function CheckInfo({
  deployMode,
}: {
  deployMode: string,
}) {
  const {
    configData,
    setConfigData,
    setCurrentStep,
    handleQuitProgress,
    setErrorVisible,
    setErrorsList,
    selectedConfig,
    errorsList,
    scenarioParam,
    loadTypeVisible,
    clusterMore,
  } = useModel('global');
  const { components = {}, auth, home_path } = configData || {};
  const {
    oceanbase = {},
    obproxy = {},
    obagent = {},
    obconfigserver = {},
    grafana = {},
    prometheus = {},
    alertmanager = {},
  } = components;
  // seekdb 模式下，自动修复后 configData.components 为后端返回结构（seekdb 对象，oceanbase 为 null）
  // 用 seekdbComp 做兜底，确保展示字段不因数据来源切换而消失
  const seekdbComp = (components as any)?.seekdb;

  const { run: handleCreateConfig, loading } = useRequest(
    createDeploymentConfig,
    {
      onSuccess: ({ success }: API.OBResponse) => {
        if (success) {
          setCurrentStep(5);
        }
      },
      onError: (e: any) => {
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  const prevStep = () => {
    setCurrentStep(3);
    window.scrollTo(0, 0);
  };

  // 当前 OB 环境是否为单机版
  const standAlone = deployMode === 'standalone';
  const seekdb = deployMode === 'seekdb';

  const handlePreCheck = async () => {
    const { data: publicKey } = await getPublicKey();
    // seekdb 模式下 appname 在 oceanbase 字段中，formatConfigData 会将其转换为 seekdb 字段
    // 需在转换前取出 appname 作为接口路径参数
    const deployName = oceanbase?.appname || (configData?.components as any)?.seekdb?.appname;
    handleCreateConfig(
      { name: deployName },
      formatConfigData(configData, seekdb ? null : scenarioParam, publicKey, seekdb, clusterMore),
    );
  };

  const getComponentsList = () => {
    const componentsList: API.TableComponentInfo[] = [];
    allComponentsKeys.forEach((key) => {
      // 只有当组件存在且有版本信息时才添加到列表
      if (components?.[key] && components?.[key]?.version) {
        const componentConfig = componentsConfig?.[key] || {};
        componentsList.push({
          ...componentConfig,
          version: components?.[key].version,
          key,
        });
      }
    });
    return componentsList;
  };

  const getComponentsNodeConfigList = () => {
    const componentsNodeConfigList: ComponentsNodeConfig[] = [];
    const tempSelectedConfig = selectedConfig.map(
      (item) => componentVersionTypeToComponent[item] || item,
    );

    let currentOnlyComponentsKeys = onlyComponentsKeys.filter(
      (key) => key !== 'obagent' && tempSelectedConfig.includes(key),
    );

    currentOnlyComponentsKeys.forEach((key) => {
      // 只有当组件配置存在且 configData 中有对应的组件数据时才添加
      if (componentsConfig?.[key] && components?.[key]) {
        componentsNodeConfigList.push({
          key,
          name: componentsConfig?.[key]?.name,
          servers: components?.[key]?.servers?.join('，'),
          isTooltip: key === obproxyComponent,
        });
      }
    });
    return componentsNodeConfigList;
  };

  const dbConfigColumns: ColumnsType<API.DBConfig> = [
    {
      title: intl.formatMessage({
        id: 'OBD.pages.components.CheckInfo.ZoneName',
        defaultMessage: 'Zone 名称',
      }),
      dataIndex: 'name',
      width: 200,
      render: (text) => text || '-',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.pages.components.CheckInfo.ObServerNodes',
        defaultMessage: 'OB Server 节点',
      }),
      dataIndex: 'servers',
      render: (text) => {
        const serversIps = text.map((item: API.OceanbaseServers) => item.ip);
        const str = serversIps.join('，');
        return (
          <Tooltip title={str} placement="topLeft">
            <div className="ellipsis">{str}</div>
          </Tooltip>
        );
      },
    },
    ...(!standAlone
      ? [
        {
          title: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.RootServerNodes',
            defaultMessage: 'Root Server 节点',
          }),
          dataIndex: 'rootservice',
          width: 200,
          render: (text) => text || '-',
        },
      ]
      : []),
  ];

  const componentsList = getComponentsList();
  const componentsNodeConfigList = getComponentsNodeConfigList();
  const initDir = `${home_path}/oceanbase/store`;
  const clusterConfigInfo = [
    {
      key: 'cluster',
      group: seekdb
        ? intl.formatMessage({
          id: 'OBD.pages.components.CheckInfo.InstanceConfiguration',
          defaultMessage: '实例配置',
        })
        : intl.formatMessage({
          id: 'OBD.pages.components.CheckInfo.ClusterConfiguration',
          defaultMessage: '集群配置',
        }),
      content: [
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.ConfigurationMode',
            defaultMessage: '配置模式',
          }),
          colSpan: 5,
          value: modeConfig[(oceanbase?.mode || seekdbComp?.mode) as keyof typeof modeConfig],
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.RootSysPassword',
            defaultMessage: 'root@sys 密码',
          }),
          colSpan: 5,
          value: (
            <Tooltip title={oceanbase?.root_password || seekdbComp?.root_password} placement="topLeft">
              <Input.Password
                value={oceanbase?.root_password || seekdbComp?.root_password}
                visibilityToggle={true}
                readOnly
                bordered={false}
                style={{ padding: 0 }}
              />
            </Tooltip>
          ),
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.DataDirectory',
            defaultMessage: '数据目录',
          }),
          value: (
            <Tooltip title={oceanbase?.data_dir || seekdbComp?.data_dir || initDir} placement="topLeft">
              <div className="ellipsis">{oceanbase?.data_dir || seekdbComp?.data_dir || initDir}</div>
            </Tooltip>
          ),
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.LogDirectory',
            defaultMessage: '日志目录',
          }),
          value: (
            <Tooltip title={oceanbase?.redo_dir || seekdbComp?.redo_dir || initDir} placement="topLeft">
              <div className="ellipsis">{oceanbase?.redo_dir || seekdbComp?.redo_dir || initDir}</div>
            </Tooltip>
          ),
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.SqlPort',
            defaultMessage: 'SQL 端口',
          }),
          colSpan: 3,
          value: oceanbase?.mysql_port || seekdbComp?.mysql_port,
        },
        ...(!seekdb ? [{
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.RpcPort',
            defaultMessage: 'RPC 端口',
          }),
          colSpan: 3,
          value: oceanbase?.rpc_port,
        }] : []),
        {
          label: intl.formatMessage({
            id: 'OBD.OCPPreCheck.CheckInfo.ConfigInfo.ObshellPort',
            defaultMessage: 'obshell 端口',
          }),
          colSpan: 3,
          value: oceanbase?.obshell_port || seekdbComp?.obshell_port,
        },
      ],

      more: oceanbase?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value))?.length
        ? [
          {
            label:
              seekdb
                ? componentsConfig[seekdbComponent].labelName :
                componentsConfig[oceanbaseComponent].labelName ||
                componentsConfig[oceanbaseStandaloneComponent].labelName,
            parameters: oceanbase?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value)),
          },
        ]
        : [],
    },
  ];

  if (selectedConfig.length) {
    let content: any[] = [],
      more: any = [];
    if (selectedConfig.includes(obproxyComponent) && obproxy) {
      content = content.concat(
        {
          label: intl.formatMessage({
            id: 'OBD.pages.Obdeploy.CheckInfo.PortObproxySql',
            defaultMessage: 'OBProxy SQL端口',
          }),
          value: obproxy?.listen_port,
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.PortObproxyExporter',
            defaultMessage: 'OBProxy Exporter 端口',
          }),
          value: obproxy?.prometheus_listen_port,
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.Obdeploy.CheckInfo.PortObproxyRpc',
            defaultMessage: 'OBProxy RPC 端口',
          }),
          value: obproxy?.rpc_listen_port,
        },
      );
      obproxy?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value))?.length &&
        more.push({
          label: componentsConfig[obproxyComponent].labelName,
          parameters: obproxy?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value)),
        });
    }
    if (selectedConfig.includes(grafanaComponent) && grafana) {
      content = content.concat({
        label: intl.formatMessage({
          id: 'OBD.Obdeploy.ClusterConfig.GrafanaServicePort',
          defaultMessage: 'Grafana 服务端口',
        }),
        value: grafana?.port,
      });
      grafana?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value))?.length &&
        more.push({
          label: componentsConfig[grafanaComponent].labelName,
          parameters: grafana?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value)),
        });
    }
    if (selectedConfig.includes(prometheusComponent) && prometheus) {
      content = content.concat({
        label: intl.formatMessage({
          id: 'OBD.Obdeploy.ClusterConfig.PrometheusServicePort',
          defaultMessage: 'Prometheus 服务端口',
        }),
        value: prometheus?.port,
      });
      prometheus?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value))?.length &&
        more.push({
          label: componentsConfig[prometheusComponent].labelName,
          parameters: prometheus?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value)),
        });
    }
    if (selectedConfig.includes(alertManagerComponent) && alertmanager) {
      content = content.concat({
        label: intl.formatMessage({
          id: 'OBD.Obdeploy.ClusterConfig.AlertManagerPort',
          defaultMessage: 'AlertManager 服务端口',
        }),
        value: alertmanager?.port,
      });
      alertmanager?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value))?.length &&
        more.push({
          label: componentsConfig[alertManagerComponent].labelName,
          parameters: alertmanager?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value)),
        });
    }

    if (selectedConfig.includes(obagentComponent) && obagent) {
      content = content.concat(
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.ObagentMonitoringServicePort',
            defaultMessage: 'OBAgent 监控服务端口',
          }),
          value: obagent?.monagent_http_port,
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.ObagentManageServicePorts',
            defaultMessage: 'OBAgent 管理服务端口',
          }),
          value: obagent?.mgragent_http_port,
        },
      );
      obagent?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value))?.length &&
        more.push({
          label: componentsConfig[obagentComponent].labelName,
          parameters: obagent?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value)),
        });
    }

    if (selectedConfig.includes(configServerComponent) && obconfigserver) {
      content = content.concat({
        label: intl.formatMessage({
          id: 'OBD.pages.Obdeploy.CheckInfo.ObconfigserverServicePort',
          defaultMessage: 'OBConfigserver 服务端口',
        }),
        value: obconfigserver?.listen_port,
      });
      obconfigserver?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value))?.length &&
        more.push({
          label: componentsConfig[configServerComponentKey].labelName,
          parameters: obconfigserver?.parameters?.filter((p: any) => p.isChanged && !p.adaptive && isExist(p.value)),
        });
    }
    clusterConfigInfo.push({
      key: 'components',
      group: intl.formatMessage({
        id: 'OBD.pages.components.CheckInfo.ComponentConfiguration',
        defaultMessage: '组件配置',
      }),
      content,
      more,
    });
    clusterConfigInfo.map((item) => {
      if (item.key === 'cluster') {
        if (selectedConfig.includes(prometheusComponent)) {
          const prometheusPasswordItem = {
            label: intl.formatMessage({
              id: 'OBD.pages.components.CheckInfo.PrometheusPassword',
              defaultMessage: 'Prometheus 密码',
            }),
            colSpan: 5,
            value: (
              <Tooltip
                title={prometheus?.basic_auth_users?.admin}
                placement="topLeft"
              >
                <Input.Password
                  value={prometheus?.basic_auth_users?.admin}
                  visibilityToggle={true}
                  readOnly
                  bordered={false}
                  style={{ padding: 0 }}
                />
              </Tooltip>
            ),
          };
          item.content.splice(2, 0, prometheusPasswordItem);
        }
        if (selectedConfig.includes(alertManagerComponent)) {
          const alertManagerPasswordItem = {
            label: intl.formatMessage({
              id: 'OBD.pages.components.CheckInfo.AlertManagerPassword',
              defaultMessage: 'AlertManager 密码',
            }),
            colSpan: 5,
            value: (
              <Tooltip
                title={alertmanager?.basic_auth_users?.admin}
                placement="topLeft"
              >
                <Input.Password
                  value={alertmanager?.basic_auth_users?.admin}
                  visibilityToggle={true}
                  readOnly
                  bordered={false}
                  style={{ padding: 0 }}
                />
              </Tooltip>
            ),
          };
          item.content.splice(2, 0, alertManagerPasswordItem);
        }
        if (selectedConfig.includes(grafanaComponent)) {
          const grafanaPasswordItem = {
            label: intl.formatMessage({
              id: 'OBD.pages.components.CheckInfo.GrafanaPassword',
              defaultMessage: 'Grafana 密码',
            }),
            colSpan: 5,
            value: (
              <Tooltip title={grafana?.login_password} placement="topLeft">
                <Input.Password
                  value={grafana?.login_password}
                  visibilityToggle={true}
                  readOnly
                  bordered={false}
                  style={{ padding: 0 }}
                />
              </Tooltip>
            ),
          };
          item.content.splice(2, 0, grafanaPasswordItem);
        }

      }
    });
  }

  useEffect(() => {
    const { obproxy = {}, alertmanager = {} } = configData.components;

    // 处理 OBProxy 密码 - 只有在 selectedConfig 包含 obproxy 时才处理
    if (selectedConfig.includes(obproxyComponent) && obproxy?.parameters) {
      // 如果没有密码，前端来随机生成一个
      const targetParam = obproxy?.parameters?.find(
        (item) => item.key === 'obproxy_sys_password',
      );
      if (!targetParam || !targetParam.value) {
        if (!targetParam) {
          const temp = { ...DEFAULT_PROXY_PWD };
          temp.value = generateRandomPassword('ob');
          obproxy?.parameters.push(temp);
        } else {
          obproxy?.parameters?.forEach((item) => {
            if (item.key === 'obproxy_sys_password') {
              item.value = generateRandomPassword('ob');
              item.adaptive = false;
              item.isChanged = true;
            }
          });
        }
        setConfigData({
          ...configData,
          components: {
            ...configData.components,
            obproxy,
          },
        });
      }
    }

    // 处理 AlertManager 密码
    if (selectedConfig.includes(alertManagerComponent) && alertmanager) {
      if (!alertmanager.basic_auth_users?.admin) {
        const newAlertmanager = {
          ...alertmanager,
          basic_auth_users: {
            ...alertmanager.basic_auth_users,
            admin: generateRandomPassword('am'),
          },
        };
        setConfigData({
          ...configData,
          components: {
            ...configData.components,
            alertmanager: newAlertmanager,
          },
        });
      }
    }

    // 处理 Prometheus 密码
    if (selectedConfig.includes(prometheusComponent) && prometheus) {
      if (!prometheus.basic_auth_users?.admin) {
        const newPrometheus = {
          ...prometheus,
          basic_auth_users: {
            ...prometheus.basic_auth_users,
            admin: generateRandomPassword('pm'),
          },
        };
        setConfigData({
          ...configData,
          components: {
            ...configData.components,
            prometheus: newPrometheus,
          },
        });
      }
    }
  }, []);

  return (
    <Space
      className={`${styles.spaceWidth} ${styles.checkInfoSpace}`}
      direction="vertical"
      size="middle"
    >
      {
        oceanbase?.topology?.length > 1 ? null : (
          <Alert
            message={seekdb
              ? intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.SeekdbInstallationInfoConfiguration',
                defaultMessage: 'seekdb 安装信息配置已完成，请检查并确认以下配置信息，确定后开始预检查。',
              })
              : intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.OceanbaseTheInstallationInformationConfiguration',
                defaultMessage: 'OceanBase 安装信息配置已完成，请检查并确认以下配置信息，确定后开始预检查。',
              })
            }
            type="info"
            showIcon
          />
        )
      }
      <ProCard className={styles.pageCard} split="horizontal">
        <Row gutter={16}>
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.components.CheckInfo.DeploymentConfiguration',
              defaultMessage: '部署配置',
            })}
            className="card-padding-bottom-24"
          >
            <Col span={12}>
              <ProCard className={styles.infoSubCard} split="vertical">
                <ProCard
                  colSpan={10}
                  title={intl.formatMessage({
                    id: 'OBD.pages.components.CheckInfo.DeploymentClusterName',
                    defaultMessage: '名称',
                  })}
                >
                  {oceanbase?.appname || seekdbComp?.appname}
                </ProCard>
                {loadTypeVisible ? (
                  <ProCard
                    colSpan={10}
                    title={intl.formatMessage({
                      id: 'OBD.pages.Obdeploy.CheckInfo.LoadType',
                      defaultMessage: '负载类型',
                    })}
                  >
                    {scenarioParam?.value.toUpperCase()}
                  </ProCard>
                ) : null}
              </ProCard>
            </Col>
          </ProCard>
          {/* 部署组件配置 */}
          <DeployedCompCheckInfo
            className="card-header-padding-top-0"
            componentsList={componentsList}
            deployMode={deployMode}
          />
        </Row>
      </ProCard>
      <ProCard className={styles.pageCard} split="horizontal">
        <Row gutter={16}>
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.components.CheckInfo.DatabaseNodeConfiguration',
              defaultMessage: '数据库节点配置',
            })}
            className="card-padding-bottom-24"
          >
            {
              seekdb ?
                <Col span={12}>
                  <ProCard
                    className={styles.infoSubCard}
                    split="vertical"
                  >
                    <div style={{ padding: '16px' }}>
                      <div style={{ color: '#8592ad', marginBottom: 8 }}>
                        {intl.formatMessage({
                          id: 'OBD.pages.components.CheckInfo.IpAddress',
                          defaultMessage: 'IP 地址',
                        })}
                      </div>
                      <div>
                        {oceanbase?.topology?.[0]?.servers
                          ?.map((item: API.OceanbaseServers) => item.ip)
                          ?.join('，')
                          || (seekdbComp?.servers as string[])?.join('，')
                          || '-'}
                      </div>
                    </div>
                  </ProCard>
                </Col>
                :
                <ProCard
                  className={styles.infoSubCard}
                  style={{ border: '1px solid #e2e8f3' }}
                  split="vertical"
                >
                  <Table
                    className={`${styles.infoCheckTable}  ob-table`}
                    columns={dbConfigColumns}
                    dataSource={oceanbase?.topology}
                    rowKey="id"
                    scroll={{ y: 300 }}
                    pagination={false}
                  />
                </ProCard>
            }
          </ProCard>
          {/* 组件节点配置 */}
          {selectedConfig.length ? (
            <CompNodeCheckInfo
              className="card-header-padding-top-0"
              componentsNodeConfigList={componentsNodeConfigList}
            />
          ) : null}
          {/* 部署用户配置 */}
          <UserCheckInfo
            title={intl.formatMessage({
              id: 'OBD.pages.components.CheckInfo.DeployUserConfiguration',
              defaultMessage: '部署用户配置',
            })}
            className="card-header-padding-top-0"
            user={auth?.user}
            password={auth?.password}
          />
          {/* 软件路径配置 */}
          <PathCheckInfo
            className="card-header-padding-top-0"
            home_path={home_path}
          />
        </Row>
      </ProCard >
      <CompDetailCheckInfo
        className="card-header-padding-top-0"
        clusterConfigInfo={clusterConfigInfo}
      />
      <footer className={styles.pageFooterContainer}>
        <div className={styles.pageFooter}>
          <Space className={styles.foolterAction}>
            <Button
              onClick={() => handleQuit(handleQuitProgress, setCurrentStep)}
              data-aspm-click="c307504.d317275"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.PreCheckExit',
                defaultMessage: '预检查-退出',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.Exit',
                defaultMessage: '退出',
              })}
            </Button>
            <Button
              onClick={prevStep}
              data-aspm-click="c307504.d317274"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.PreCheckPreviousStep',
                defaultMessage: '预检查-上一步',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.PreviousStep',
                defaultMessage: '上一步',
              })}
            </Button>
            <Button
              type="primary"
              onClick={handlePreCheck}
              loading={loading}
              data-aspm-click="c307504.d317273"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.PreCheck',
                defaultMessage: '预检查-预检查',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.PreCheck.1',
                defaultMessage: '预检查',
              })}
            </Button>
          </Space>
        </div>
      </footer>
    </Space >
  );
}
