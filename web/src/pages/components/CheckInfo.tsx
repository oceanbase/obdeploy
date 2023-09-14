import { intl } from '@/utils/intl';
import { useState } from 'react';
import { useModel } from 'umi';
import { Space, Button, Table, Row, Col, Alert, Tooltip } from 'antd';
import { ProCard } from '@ant-design/pro-components';
import type { ColumnsType } from 'antd/es/table';
import { EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons';
import useRequest from '@/utils/useRequest';
import { createDeploymentConfig } from '@/services/ob-deploy-web/Deployments';
import { handleQuit, getErrorInfo } from '@/utils';
import {
  componentsConfig,
  allComponentsKeys,
  onlyComponentsKeys,
  modeConfig,
  obproxyComponent,
} from '../constants';
import { getLocale } from 'umi';
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

export default function CheckInfo() {
  const {
    configData,
    setCheckOK,
    lowVersion,
    setCurrentStep,
    handleQuitProgress,
    setErrorVisible,
    setErrorsList,
    selectedConfig,
    errorsList,
  } = useModel('global');
  const { components = {}, auth, home_path } = configData || {};
  const {
    oceanbase = {},
    obproxy = {},
    ocpexpress = {},
    obagent = {},
  } = components;
  const [showPwd, setShowPwd] = useState(false);

  const { run: handleCreateConfig, loading } = useRequest(
    createDeploymentConfig,
    {
      onSuccess: ({ success }: API.OBResponse) => {
        if (success) {
          setCheckOK(true);
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

  const handlePreCheck = () => {
    handleCreateConfig({ name: oceanbase?.appname }, { ...configData });
  };

  const getComponentsList = () => {
    const componentsList: API.TableComponentInfo[] = [];
    allComponentsKeys.forEach((key) => {
      if (components?.[key]) {
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
    //todo:待优化
    let _selectedConfig = [...selectedConfig];
    _selectedConfig.forEach((item, idx) => {
      if (item === 'ocp-express') {
        _selectedConfig[idx] = 'ocpexpress';
      }
    });
    let currentOnlyComponentsKeys = onlyComponentsKeys.filter(
      (key) => key !== 'obagent' && _selectedConfig.includes(key),
    );

    if (lowVersion) {
      currentOnlyComponentsKeys = currentOnlyComponentsKeys.filter(
        (key) => key !== 'ocpexpress',
      );
    }

    currentOnlyComponentsKeys.forEach((key) => {
      if (componentsConfig?.[key]) {
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
    {
      title: intl.formatMessage({
        id: 'OBD.pages.components.CheckInfo.RootServerNodes',
        defaultMessage: 'Root Server 节点',
      }),
      dataIndex: 'rootservice',
      width: 200,
      render: (text) => text || '-',
    },
  ];

  const getMoreColumns = (label: string) => {
    const columns: ColumnsType<API.MoreParameter> = [
      {
        title: label,
        dataIndex: 'key',
        render: (text) => text,
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.components.CheckInfo.ParameterValue',
          defaultMessage: '参数值',
        }),
        dataIndex: 'value',
        render: (text, record) =>
          record.adaptive
            ? intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.Adaptive',
                defaultMessage: '自动分配',
              })
            : text || '-',
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.components.CheckInfo.Introduction',
          defaultMessage: '介绍',
        }),
        dataIndex: 'description',
        render: (text) => (
          <Tooltip title={text} placement="topLeft">
            <div className="ellipsis">{text}</div>
          </Tooltip>
        ),
      },
    ];

    return columns;
  };

  const componentsList = getComponentsList();
  const componentsNodeConfigList = getComponentsNodeConfigList();
  const initDir = `${home_path}/oceanbase/store`;
  const clusterConfigInfo = [
    {
      key: 'cluster',
      group: intl.formatMessage({
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
          value: modeConfig[oceanbase?.mode],
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.RootSysPassword',
            defaultMessage: 'root@sys 密码',
          }),
          colSpan: 5,
          value: (
            <Tooltip title={oceanbase?.root_password} placement="topLeft">
              <div className="ellipsis">{oceanbase?.root_password}</div>
            </Tooltip>
          ),
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.DataDirectory',
            defaultMessage: '数据目录',
          }),
          value: (
            <Tooltip title={oceanbase?.data_dir || initDir} placement="topLeft">
              <div className="ellipsis">{oceanbase?.data_dir || initDir}</div>
            </Tooltip>
          ),
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.LogDirectory',
            defaultMessage: '日志目录',
          }),
          value: (
            <Tooltip title={oceanbase?.redo_dir || initDir} placement="topLeft">
              <div className="ellipsis">{oceanbase?.redo_dir || initDir}</div>
            </Tooltip>
          ),
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.SqlPort',
            defaultMessage: 'SQL 端口',
          }),
          colSpan: 3,
          value: oceanbase?.mysql_port,
        },
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.RpcPort',
            defaultMessage: 'RPC 端口',
          }),
          colSpan: 3,
          value: oceanbase?.rpc_port,
        },
      ],

      more: oceanbase?.parameters?.length
        ? [
            {
              label: componentsConfig['oceanbase'].labelName,
              parameters: oceanbase?.parameters,
            },
          ]
        : [],
    },
  ];

  if (selectedConfig.length) {
    let content: any[] = [],
      more: any = [];
    if (selectedConfig.includes('obproxy')) {
      content = content.concat(
        {
          label: intl.formatMessage({
            id: 'OBD.pages.components.CheckInfo.ObproxyServicePort',
            defaultMessage: 'OBProxy 服务端口',
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
      );
      obproxy?.parameters?.length &&
        more.push({
          label: componentsConfig['obproxy'].labelName,
          parameters: obproxy?.parameters,
        });
    }

    if (selectedConfig.includes('obagent')) {
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
      obagent?.parameters?.length &&
        more.push({
          label: componentsConfig['obagent'].labelName,
          parameters: obagent?.parameters,
        });
    }
    // more是否有数据跟前面是否打开更多配置有关
    if (!lowVersion && selectedConfig.includes('ocp-express')) {
      content.push({
        label: intl.formatMessage({
          id: 'OBD.pages.components.CheckInfo.PortOcpExpress',
          defaultMessage: 'OCP Express 端口',
        }),
        value: ocpexpress?.port,
      });
      ocpexpress?.parameters?.length &&
        more.push({
          label: componentsConfig['ocpexpress'].labelName,
          parameters: ocpexpress?.parameters,
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
  }

  return (
    <Space
      className={`${styles.spaceWidth} ${styles.checkInfoSpace}`}
      direction="vertical"
      size="middle"
    >
      <Alert
        message={intl.formatMessage({
          id: 'OBD.pages.components.CheckInfo.OceanbaseTheInstallationInformationConfiguration',
          defaultMessage:
            'OceanBase 安装信息配置已完成，请检查并确认以下配置信息，确定后开始预检查。',
        })}
        type="info"
        showIcon
      />

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
                    defaultMessage: '部署集群名称',
                  })}
                >
                  {oceanbase?.appname}
                </ProCard>
              </ProCard>
            </Col>
          </ProCard>
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.components.CheckInfo.DeployComponents',
              defaultMessage: '部署组件',
            })}
            className="card-header-padding-top-0 card-padding-bottom-24 "
          >
            <Row gutter={16}>
              {componentsList.map(
                (item: API.TableComponentInfo, index: number) => (
                  <Col
                    span={12}
                    style={index > 1 ? { marginTop: 16 } : {}}
                    key={item.key}
                  >
                    <ProCard
                      className={styles.infoSubCard}
                      split="vertical"
                      key={item.key}
                    >
                      <ProCard
                        colSpan={10}
                        title={intl.formatMessage({
                          id: 'OBD.pages.components.CheckInfo.Component',
                          defaultMessage: '组件',
                        })}
                      >
                        {item?.showComponentName}
                      </ProCard>
                      <ProCard
                        colSpan={7}
                        title={intl.formatMessage({
                          id: 'OBD.pages.components.CheckInfo.Type',
                          defaultMessage: '类型',
                        })}
                      >
                        {componentsConfig[item.key]?.type}
                      </ProCard>
                      <ProCard
                        colSpan={7}
                        title={intl.formatMessage({
                          id: 'OBD.pages.components.CheckInfo.Version',
                          defaultMessage: '版本',
                        })}
                      >
                        {item?.version}
                      </ProCard>
                    </ProCard>
                  </Col>
                ),
              )}
            </Row>
          </ProCard>
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
          </ProCard>
          {selectedConfig.length ? (
            <ProCard
              title={intl.formatMessage({
                id: 'OBD.pages.components.CheckInfo.ComponentNodeConfiguration',
                defaultMessage: '组件节点配置',
              })}
              className="card-header-padding-top-0 card-padding-bottom-24"
            >
              <Col span={componentsNodeConfigList?.length === 1 ? 12 : 24}>
                <ProCard className={styles.infoSubCard} split="vertical">
                  {componentsNodeConfigList.map(
                    (item: ComponentsNodeConfig) => (
                      <ProCard title={item.name} key={item.key}>
                        {item.isTooltip ? (
                          <Tooltip title={item?.servers} placement="topLeft">
                            <div className="ellipsis">{item?.servers}</div>
                          </Tooltip>
                        ) : (
                          item?.servers
                        )}
                      </ProCard>
                    ),
                  )}
                </ProCard>
              </Col>
            </ProCard>
          ) : null}
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.components.CheckInfo.DeployUserConfiguration',
              defaultMessage: '部署用户配置',
            })}
            className="card-header-padding-top-0 card-padding-bottom-24"
          >
            <Col span={12}>
              <ProCard className={styles.infoSubCard} split="vertical">
                <ProCard
                  title={intl.formatMessage({
                    id: 'OBD.pages.components.CheckInfo.Username',
                    defaultMessage: '用户名',
                  })}
                >
                  {auth?.user}
                </ProCard>
                <ProCard
                  title={intl.formatMessage({
                    id: 'OBD.pages.components.CheckInfo.Password',
                    defaultMessage: '密码',
                  })}
                >
                  {auth?.password ? (
                    <div style={{ position: 'relative' }}>
                      {showPwd ? (
                        <div>
                          <Tooltip title={auth?.password} placement="topLeft">
                            <div
                              className="ellipsis"
                              style={{ width: 'calc(100% - 20px)' }}
                            >
                              {auth?.password}
                            </div>
                          </Tooltip>
                          <EyeOutlined
                            className={styles.pwdIcon}
                            onClick={() => setShowPwd(false)}
                          />
                        </div>
                      ) : (
                        <div>
                          ******
                          <EyeInvisibleOutlined
                            className={styles.pwdIcon}
                            onClick={() => setShowPwd(true)}
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    '-'
                  )}
                </ProCard>
              </ProCard>
            </Col>
          </ProCard>
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.components.CheckInfo.SoftwarePathConfiguration',
              defaultMessage: '软件路径配置',
            })}
            className="card-header-padding-top-0 card-padding-bottom-24"
          >
            <Col span={12}>
              <ProCard className={styles.infoSubCard} split="vertical">
                <ProCard
                  title={intl.formatMessage({
                    id: 'OBD.pages.components.CheckInfo.SoftwarePath',
                    defaultMessage: '软件路径',
                  })}
                >
                  <Tooltip title={home_path} placement="topLeft">
                    {home_path}
                  </Tooltip>
                </ProCard>
              </ProCard>
            </Col>
          </ProCard>
        </Row>
      </ProCard>
      <ProCard split="horizontal">
        <Row gutter={16}>
          {clusterConfigInfo?.map((item, index) => (
            <ProCard
              title={item.group}
              key={item.key}
              className={`${
                index === clusterConfigInfo?.length - 1
                  ? 'card-header-padding-top-0 card-padding-bottom-24'
                  : 'card-padding-bottom-24'
              }`}
            >
              <Col span={24}>
                <ProCard className={styles.infoSubCard} split="vertical">
                  {item.content.map((subItem) => (
                    <ProCard
                      title={subItem.label}
                      key={subItem.label}
                      colSpan={subItem.colSpan}
                    >
                      {subItem.value}
                    </ProCard>
                  ))}
                </ProCard>
              </Col>
              {item?.more?.length ? (
                <Space
                  direction="vertical"
                  size="middle"
                  style={{ marginTop: 16 }}
                >
                  {item?.more.map((moreItem) => (
                    <ProCard
                      className={styles.infoSubCard}
                      style={{ border: '1px solid #e2e8f3' }}
                      split="vertical"
                      key={moreItem.label}
                    >
                      <Table
                        className={`${styles.infoCheckTable}  ob-table`}
                        columns={getMoreColumns(moreItem.label)}
                        dataSource={moreItem?.parameters}
                        pagination={false}
                        scroll={{ y: 300 }}
                        rowKey="key"
                      />
                    </ProCard>
                  ))}
                </Space>
              ) : null}
            </ProCard>
          ))}
        </Row>
      </ProCard>
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
    </Space>
  );
}
