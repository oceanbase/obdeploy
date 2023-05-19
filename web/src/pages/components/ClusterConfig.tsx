import { intl } from '@/utils/intl';
import { useState, useEffect } from 'react';
import { useModel } from 'umi';
import {
  Space,
  Button,
  Tooltip,
  Row,
  Switch,
  Table,
  Spin,
  Form,
  message,
} from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import {
  ProCard,
  ProForm,
  ProFormText,
  ProFormRadio,
  ProFormDigit,
} from '@ant-design/pro-components';
import type { ColumnsType } from 'antd/es/table';
import { handleQuit, getErrorInfo, getRandomPassword } from '@/utils';
import useRequest from '@/utils/useRequest';
import { queryComponentParameters } from '@/services/ob-deploy-web/Components';
import Parameter from './Parameter';
import TooltipInput from './TooltipInput';
import {
  commonStyle,
  pathRule,
  onlyComponentsKeys,
  componentsConfig,
  componentVersionTypeToComponent,
} from '../constants';
import { getLocale } from 'umi';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

interface Parameter extends API.Parameter {
  description?: string;
}

interface FormValues extends API.Components {
  oceanbase?: {
    mode?: string;
    parameters?: any;
  };
}

const showConfigKeys = {
  oceanbase: [
    'home_path',
    'mode',
    'root_password',
    'data_dir',
    'redo_dir',
    'mysql_port',
    'rpc_port',
  ],

  obproxy: ['home_path', 'listen_port', 'prometheus_listen_port'],
  obagent: ['home_path', 'monagent_http_port', 'mgragent_http_port'],
  ocpexpress: ['home_path', 'port'],
};

export default function ClusterConfig() {
  const {
    setCurrentStep,
    configData,
    setConfigData,
    currentType,
    lowVersion,
    clusterMore,
    setClusterMore,
    componentsMore,
    setComponentsMore,
    clusterMoreConfig,
    setClusterMoreConfig,
    componentsMoreConfig,
    setComponentsMoreConfig,
    handleQuitProgress,
    setErrorVisible,
    setErrorsList,
    errorsList,
  } = useModel('global');
  const { components = {}, home_path } = configData || {};
  const {
    oceanbase = {},
    ocpexpress = {},
    obproxy = {},
    obagent = {},
  } = components;
  const [form] = ProForm.useForm();
  const [currentMode, setCurrentMode] = useState(
    oceanbase?.mode || 'PRODUCTION',
  );

  const [passwordVisible, setPasswordVisible] = useState(true);
  const [clusterMoreLoading, setClusterMoreLoading] = useState(false);
  const [componentsMoreLoading, setComponentsMoreLoading] = useState(false);
  const { run: getMoreParamsters } = useRequest(queryComponentParameters);

  const formatParameters = (dataSource: any) => {
    if (dataSource) {
      const parameterKeys = Object.keys(dataSource);
      return parameterKeys.map((key) => {
        const { params, ...rest } = dataSource[key];
        return {
          key,
          ...rest,
          ...params,
        };
      });
    } else {
      return [];
    }
  };

  const setData = (dataSource: FormValues) => {
    let newComponents: API.Components = { ...components };
    if (currentType === 'all') {
      newComponents.obproxy = {
        ...(components.obproxy || {}),
        ...dataSource.obproxy,
        parameters: formatParameters(dataSource.obproxy?.parameters),
      };
      if (!lowVersion) {
        newComponents.ocpexpress = {
          ...(components.ocpexpress || {}),
          ...dataSource.ocpexpress,
          parameters: formatParameters(dataSource.ocpexpress?.parameters),
        };
      }
      newComponents.obagent = {
        ...(components.obagent || {}),
        ...dataSource.obagent,
        parameters: formatParameters(dataSource.obagent?.parameters),
      };
    }
    newComponents.oceanbase = {
      ...(components.oceanbase || {}),
      ...dataSource.oceanbase,
      parameters: formatParameters(dataSource.oceanbase?.parameters),
    };
    setConfigData({ ...configData, components: newComponents });
  };

  const prevStep = () => {
    const formValues = form.getFieldsValue(true);
    setData(formValues);
    setCurrentStep(2);
    setErrorVisible(false);
    setErrorsList([]);
    window.scrollTo(0, 0);
  };

  const nextStep = () => {
    form
      .validateFields()
      .then((values) => {
        setData(values);
        setCurrentStep(4);
        setErrorVisible(false);
        setErrorsList([]);
        window.scrollTo(0, 0);
      })
      .catch(({ errorFields }) => {
        const errorName = errorFields?.[0].name;
        form.scrollToField(errorName);
        message.destroy();
        if (errorName.includes('parameters')) {
          message.warning(
            intl.formatMessage({
              id: 'OBD.pages.components.ClusterConfig.RequiredParametersForMoreConfigurations',
              defaultMessage: '更多配置有必填参数未填入',
            }),
          );
        }
      });
  };

  const onValuesChange = (values: FormValues) => {
    if (values?.oceanbase?.mode) {
      setCurrentMode(values?.oceanbase?.mode);
    }
  };

  const portValidator = (_: any, value: number) => {
    if (value) {
      if (value >= 1024 && value <= 65535) {
        return Promise.resolve();
      }
      return Promise.reject(
        new Error(
          intl.formatMessage({
            id: 'OBD.pages.components.ClusterConfig.ThePortNumberCanOnly',
            defaultMessage: '端口号只支持 1024~65535 范围',
          }),
        ),
      );
    }
  };

  const formatMoreConfig = (dataSource: API.ParameterMeta[]) => {
    return dataSource.map((item) => {
      const component = componentVersionTypeToComponent[item.component]
        ? componentVersionTypeToComponent[item.component]
        : item.component;
      const componentConfig = componentsConfig[component];
      // filter out existing parameters
      let configParameter = item?.config_parameters.filter((parameter) => {
        return !showConfigKeys?.[componentConfig.componentKey]?.includes(
          parameter.name,
        );
      });
      const newConfigParameter: API.NewConfigParameter[] = configParameter.map(
        (parameterItem) => {
          return {
            ...parameterItem,
            parameterValue: {
              value: parameterItem.default,
              adaptive: parameterItem.auto,
              auto: parameterItem.auto,
              require: parameterItem.require,
            },
          };
        },
      );

      const result: API.NewParameterMeta = {
        ...item,
        componentKey: componentConfig.componentKey,
        label: componentConfig.labelName,
        configParameter: newConfigParameter,
      };
      return result;
    });
  };

  const getInitialParameters = (
    currentComponent: string,
    dataSource: API.MoreParameter[],
    data: API.NewParameterMeta[],
  ) => {
    const currentComponentNameConfig = data?.filter(
      (item) => item.component === currentComponent,
    )?.[0];
    if (currentComponentNameConfig) {
      const parameters: any = {};
      currentComponentNameConfig.configParameter.forEach((item) => {
        let parameter = {
          ...item,
          key: item.name,
          params: {
            value: item.default,
            adaptive: item.auto,
            auto: item.auto,
            require: item.require,
          },
        };
        dataSource?.some((dataItem) => {
          if (item.name === dataItem.key) {
            parameter = {
              key: dataItem.key,
              description: parameter.description,
              params: {
                ...parameter.params,
                ...dataItem,
              },
            };
            return true;
          }
          return false;
        });
        parameters[item.name] = parameter;
      });
      return parameters;
    } else {
      return undefined;
    }
  };

  const getClusterMoreParamsters = async () => {
    setClusterMoreLoading(true);
    try {
      const { success, data } = await getMoreParamsters(
        {},
        {
          filters: [
            {
              component: oceanbase?.component,
              version: oceanbase?.version,
              is_essential_only: true,
            },
          ],
        },
      );
      if (success) {
        const newClusterMoreConfig = formatMoreConfig(data?.items);
        setClusterMoreConfig(newClusterMoreConfig);
        form.setFieldsValue({
          oceanbase: {
            parameters: getInitialParameters(
              oceanbase?.component,
              oceanbase?.parameters,
              newClusterMoreConfig,
            ),
          },
        });
      }
    } catch (e: any) {
      setClusterMore(false);
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    }
    setClusterMoreLoading(false);
  };

  const getComponentsMoreParamsters = async () => {
    const filters: API.ParameterFilter[] = [];
    let currentOnlyComponentsKeys: string[] = onlyComponentsKeys;
    if (lowVersion) {
      currentOnlyComponentsKeys = onlyComponentsKeys.filter(
        (key) => key !== 'ocpexpress',
      );
    }
    currentOnlyComponentsKeys.forEach((item) => {
      if (components[item]) {
        filters.push({
          component: components[item]?.component,
          version: components[item]?.version,
          is_essential_only: true,
        });
      }
    });
    setComponentsMoreLoading(true);
    try {
      const { success, data } = await getMoreParamsters({}, { filters });
      if (success) {
        const newComponentsMoreConfig = formatMoreConfig(data?.items);
        setComponentsMoreConfig(newComponentsMoreConfig);
        const setValues = {
          obproxy: {
            parameters: getInitialParameters(
              obproxy?.component,
              obproxy?.parameters,
              newComponentsMoreConfig,
            ),
          },
          obagent: {
            parameters: getInitialParameters(
              obagent?.component,
              obagent?.parameters,
              newComponentsMoreConfig,
            ),
          },
        };
        if (!lowVersion) {
          setValues.ocpexpress = {
            parameters: getInitialParameters(
              ocpexpress?.component,
              ocpexpress?.parameters,
              newComponentsMoreConfig,
            ),
          };
        }
        form.setFieldsValue(setValues);
      }
    } catch (e) {
      setComponentsMore(false);
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    }

    setComponentsMoreLoading(false);
  };

  const handleCluserMoreChange = (checked: boolean) => {
    setClusterMore(checked);
    if (!clusterMoreConfig?.length) {
      getClusterMoreParamsters();
    }
  };

  const handleComponentsMoreChange = (checked: boolean) => {
    setComponentsMore(checked);
    if (!componentsMoreConfig?.length) {
      getComponentsMoreParamsters();
    }
  };

  const parameterValidator = (_: any, value?: API.ParameterValue) => {
    if (value?.adaptive) {
      return Promise.resolve();
    } else if (value?.require && !value?.value) {
      return Promise.reject(
        new Error(
          intl.formatMessage({
            id: 'OBD.pages.components.ClusterConfig.RequiredForCustomParameters',
            defaultMessage: '自定义参数时必填',
          }),
        ),
      );
    }
    return Promise.resolve();
  };

  const getMoreColumns = (label: string, componentKey: string) => {
    const columns: ColumnsType<API.NewConfigParameter> = [
      {
        title: label,
        dataIndex: 'name',
        width: 250,
        render: (text) => text || '-',
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.components.ClusterConfig.ParameterValue',
          defaultMessage: '参数值',
        }),
        width: locale === 'zh-CN' ? 240 : 320,
        dataIndex: 'parameterValue',
        render: (text, record) => {
          return (
            <Form.Item
              className={styles.inlineFormItem}
              name={[componentKey, 'parameters', record.name || '', 'params']}
              rules={[{ validator: parameterValidator }]}
            >
              <Parameter />
            </Form.Item>
          );
        },
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.components.ClusterConfig.Introduction',
          defaultMessage: '介绍',
        }),
        dataIndex: 'description',
        render: (text, record) =>
          text ? (
            <Form.Item
              className={styles.inlineFormItem}
              name={[
                componentKey,
                'parameters',
                record.name || '',
                'description',
              ]}
            >
              <Tooltip title={text}>
                <div className="ellipsis">{text}</div>
              </Tooltip>
            </Form.Item>
          ) : (
            '-'
          ),
      },
    ];

    return columns;
  };

  const getTableConfig = (
    showVisible: boolean,
    dataSource: API.NewParameterMeta[],
    loading: boolean,
  ) => {
    return showVisible ? (
      <Spin spinning={loading}>
        <Space
          className={styles.spaceWidth}
          direction="vertical"
          size="middle"
          style={{ minHeight: 50, marginTop: 16 }}
        >
          {dataSource.map((moreItem) => (
            <ProCard
              className={styles.infoSubCard}
              style={{ border: '1px solid #e2e8f3' }}
              split="vertical"
              key={moreItem.component}
            >
              <Table
                className={`${styles.moreConfigTable} ob-table`}
                columns={getMoreColumns(moreItem.label, moreItem.componentKey)}
                rowKey="name"
                dataSource={moreItem.configParameter}
                scroll={{ y: 300 }}
                pagination={false}
              />
            </ProCard>
          ))}
        </Space>
      </Spin>
    ) : null;
  };

  useEffect(() => {
    if (clusterMore && !clusterMoreConfig?.length) {
      getClusterMoreParamsters();
    }
    if (componentsMore && !componentsMoreConfig?.length) {
      getComponentsMoreParamsters();
    }
  }, []);

  const initPassword = getRandomPassword();

  const initialValues = {
    oceanbase: {
      mode: oceanbase?.mode || 'PRODUCTION',
      root_password: oceanbase?.root_password || initPassword,
      data_dir: oceanbase?.data_dir || undefined,
      redo_dir: oceanbase?.redo_dir || undefined,
      mysql_port: oceanbase?.mysql_port || 2881,
      rpc_port: oceanbase?.rpc_port || 2882,
      parameters: getInitialParameters(
        oceanbase?.component,
        oceanbase?.parameters,
        clusterMoreConfig,
      ),
    },
    obproxy: {
      listen_port: obproxy?.listen_port || 2883,
      prometheus_listen_port: obproxy?.prometheus_listen_port || 2884,
      parameters: getInitialParameters(
        obproxy?.component,
        obproxy?.parameters,
        componentsMoreConfig,
      ),
    },
    obagent: {
      monagent_http_port: obagent?.monagent_http_port || 8088,
      mgragent_http_port: obagent?.mgragent_http_port || 8089,
      parameters: getInitialParameters(
        obagent?.component,
        obagent?.parameters,
        componentsMoreConfig,
      ),
    },
  };

  if (!lowVersion) {
    initialValues.ocpexpress = {
      port: ocpexpress?.port || 8180,
      parameters: getInitialParameters(
        ocpexpress?.component,
        ocpexpress?.parameters,
        componentsMoreConfig,
      ),
    };
  }

  const singleItemStyle = { width: 448 };
  const initDir = `${home_path}/oceanbase/store`;

  return (
    <ProForm
      form={form}
      submitter={false}
      initialValues={initialValues}
      onValuesChange={onValuesChange}
      scrollToFirstError
    >
      <Space className={styles.spaceWidth} direction="vertical" size="middle">
        <ProCard className={styles.pageCard} split="horizontal">
          <ProCard
            title={intl.formatMessage({
              id: 'OBD.pages.components.ClusterConfig.ClusterConfiguration',
              defaultMessage: '集群配置',
            })}
            className="card-padding-bottom-24"
          >
            <ProFormRadio.Group
              name={['oceanbase', 'mode']}
              fieldProps={{ optionType: 'button', style: { marginBottom: 16 } }}
              label={intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.ModeConfiguration',
                defaultMessage: '模式配置',
              })}
              options={[
                {
                  label: intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.MaximumOccupancy',
                    defaultMessage: '最大占用',
                  }),
                  value: 'PRODUCTION',
                },
                {
                  label: intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.MinimumAvailability',
                    defaultMessage: '最小可用',
                  }),
                  value: 'DEMO',
                },
              ]}
            />
            <a
              className={styles.viewRule}
              href="https://www.oceanbase.com/docs/obd-cn"
              target="_blank"
              data-aspm-click="c307508.d326703"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.ClusterConfigurationViewModeConfiguration',
                defaultMessage: '集群配置-查看模式配置规则',
              })}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.ViewModeConfigurationRules',
                defaultMessage: '查看模式配置规则',
              })}
            </a>
            <div className={styles.modeExtra}>
              <div className={styles.modeExtraContent}>
                {currentMode === 'PRODUCTION'
                  ? intl.formatMessage({
                      id: 'OBD.pages.components.ClusterConfig.ThisModeWillMaximizeThe',
                      defaultMessage:
                        '此模式将最大化利用环境资源，保证集群的性能与稳定性，推荐使用此模式。',
                    })
                  : intl.formatMessage({
                      id: 'OBD.pages.components.ClusterConfig.ConfigureResourceParametersThatMeet',
                      defaultMessage: '配置满足集群正常运行的资源参数',
                    })}
              </div>
            </div>
            <ProFormText.Password
              name={['oceanbase', 'root_password']}
              label={intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.RootSysPassword',
                defaultMessage: 'root@sys 密码',
              })}
              fieldProps={{
                style: singleItemStyle,
                autoComplete: 'new-password',
                visibilityToggle: {
                  visible: passwordVisible,
                  onVisibleChange: setPasswordVisible,
                },
              }}
              placeholder={intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                defaultMessage: '请输入',
              })}
              rules={[
                {
                  required: true,
                  message: intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                    defaultMessage: '请输入',
                  }),
                },
                {
                  pattern: /^[0-9a-zA-Z~!@#%^&*_\-+=|(){}\[\]:;,.?/]{8,32}$/,
                  message: intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.OnlyEnglishNumbersAndSpecial',
                    defaultMessage:
                      '仅支持英文、数字和特殊字符（~!@#%^&*_-+=|(){}[]:;,.?/），长度在 8-32 个字符之内',
                  }),
                },
              ]}
            />

            <Row>
              <Space direction="vertical" size={0}>
                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.DataDirectory',
                    defaultMessage: '数据目录',
                  })}
                  name={['oceanbase', 'data_dir']}
                  rules={[pathRule]}
                >
                  <TooltipInput placeholder={initDir} name="data_dir" />
                </Form.Item>
                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.LogDirectory',
                    defaultMessage: '日志目录',
                  })}
                  name={['oceanbase', 'redo_dir']}
                  rules={[pathRule]}
                >
                  <TooltipInput placeholder={initDir} name="redo_dir" />
                </Form.Item>
              </Space>
            </Row>
            <Row>
              <Space size="middle">
                <ProFormDigit
                  name={['oceanbase', 'mysql_port']}
                  label={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.SqlPort',
                    defaultMessage: 'SQL 端口',
                  })}
                  fieldProps={{ style: commonStyle }}
                  placeholder={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                    defaultMessage: '请输入',
                  })}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                        defaultMessage: '请输入',
                      }),
                    },
                    { validator: portValidator },
                  ]}
                />

                <ProFormDigit
                  name={['oceanbase', 'rpc_port']}
                  label={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.RpcPort',
                    defaultMessage: 'RPC 端口',
                  })}
                  fieldProps={{ style: commonStyle }}
                  placeholder={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                    defaultMessage: '请输入',
                  })}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                        defaultMessage: '请输入',
                      }),
                    },
                    { validator: portValidator },
                  ]}
                />
              </Space>
            </Row>
            <div className={styles.moreSwitch}>
              {intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.MoreConfigurations',
                defaultMessage: '更多配置',
              })}

              <Switch
                className="ml-20"
                checked={clusterMore}
                onChange={handleCluserMoreChange}
              />
            </div>
            {clusterMore
              ? getTableConfig(
                  clusterMore,
                  clusterMoreConfig,
                  clusterMoreLoading,
                )
              : null}
          </ProCard>
        </ProCard>
        {currentType === 'all' ? (
          <ProCard className={styles.pageCard} split="horizontal">
            <ProCard
              title={intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.ComponentConfiguration',
                defaultMessage: '组件配置',
              })}
              className="card-padding-bottom-24"
            >
              <Row>
                <Space size="middle">
                  <ProFormDigit
                    name={['obproxy', 'listen_port']}
                    label={intl.formatMessage({
                      id: 'OBD.pages.components.ClusterConfig.ObproxyServicePort',
                      defaultMessage: 'OBProxy 服务端口',
                    })}
                    fieldProps={{ style: commonStyle }}
                    placeholder={intl.formatMessage({
                      id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                      defaultMessage: '请输入',
                    })}
                    rules={[
                      {
                        required: true,
                        message: intl.formatMessage({
                          id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                          defaultMessage: '请输入',
                        }),
                      },
                      { validator: portValidator },
                    ]}
                  />

                  <ProFormDigit
                    name={['obproxy', 'prometheus_listen_port']}
                    label={
                      <>
                        {intl.formatMessage({
                          id: 'OBD.pages.components.ClusterConfig.PortObproxyExporter',
                          defaultMessage: 'OBProxy Exporter 端口',
                        })}

                        <Tooltip
                          title={intl.formatMessage({
                            id: 'OBD.pages.components.ClusterConfig.PortObproxyOfExporterIs',
                            defaultMessage:
                              'OBProxy 的 Exporter 端口，用于 Prometheus 拉取 OBProxy 监控数据。',
                          })}
                        >
                          <QuestionCircleOutlined className="ml-10" />
                        </Tooltip>
                      </>
                    }
                    fieldProps={{ style: commonStyle }}
                    placeholder={intl.formatMessage({
                      id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                      defaultMessage: '请输入',
                    })}
                    rules={[
                      {
                        required: true,
                        message: intl.formatMessage({
                          id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                          defaultMessage: '请输入',
                        }),
                      },
                      { validator: portValidator },
                    ]}
                  />
                </Space>
              </Row>
              <Row>
                <Space size="middle">
                  <ProFormDigit
                    name={['obagent', 'monagent_http_port']}
                    label={intl.formatMessage({
                      id: 'OBD.pages.components.ClusterConfig.ObagentMonitoringServicePort',
                      defaultMessage: 'OBAgent 监控服务端口',
                    })}
                    fieldProps={{ style: commonStyle }}
                    placeholder={intl.formatMessage({
                      id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                      defaultMessage: '请输入',
                    })}
                    rules={[
                      {
                        required: true,
                        message: intl.formatMessage({
                          id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                          defaultMessage: '请输入',
                        }),
                      },
                      { validator: portValidator },
                    ]}
                  />

                  <ProFormDigit
                    name={['obagent', 'mgragent_http_port']}
                    label={intl.formatMessage({
                      id: 'OBD.pages.components.ClusterConfig.ObagentManageServicePorts',
                      defaultMessage: 'OBAgent 管理服务端口',
                    })}
                    fieldProps={{ style: commonStyle }}
                    placeholder={intl.formatMessage({
                      id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                      defaultMessage: '请输入',
                    })}
                    rules={[
                      {
                        required: true,
                        message: intl.formatMessage({
                          id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                          defaultMessage: '请输入',
                        }),
                      },
                      { validator: portValidator },
                    ]}
                  />
                </Space>
              </Row>
              {!lowVersion ? (
                <Row>
                  <ProFormDigit
                    name={['ocpexpress', 'port']}
                    label={intl.formatMessage({
                      id: 'OBD.pages.components.ClusterConfig.PortOcpExpress',
                      defaultMessage: 'OCP Express 端口',
                    })}
                    fieldProps={{ style: commonStyle }}
                    placeholder={intl.formatMessage({
                      id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                      defaultMessage: '请输入',
                    })}
                    rules={[
                      {
                        required: true,
                        message: intl.formatMessage({
                          id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                          defaultMessage: '请输入',
                        }),
                      },
                      { validator: portValidator },
                    ]}
                  />
                </Row>
              ) : null}
              <div className={styles.moreSwitch}>
                {intl.formatMessage({
                  id: 'OBD.pages.components.ClusterConfig.MoreConfigurations',
                  defaultMessage: '更多配置',
                })}

                <Switch
                  className="ml-20"
                  checked={componentsMore}
                  onChange={handleComponentsMoreChange}
                />
              </div>
              {componentsMore
                ? getTableConfig(
                    componentsMore,
                    componentsMoreConfig,
                    componentsMoreLoading,
                  )
                : null}
            </ProCard>
          </ProCard>
        ) : null}
        <footer className={styles.pageFooterContainer}>
          <div className={styles.pageFooter}>
            <Space className={styles.foolterAction}>
              <Button
                onClick={() => handleQuit(handleQuitProgress, setCurrentStep)}
                data-aspm-click="c307508.d317282"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.pages.components.ClusterConfig.ClusterConfigurationExit',
                  defaultMessage: '集群配置-退出',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.pages.components.ClusterConfig.Exit',
                  defaultMessage: '退出',
                })}
              </Button>
              <Tooltip
                title={intl.formatMessage({
                  id: 'OBD.pages.components.ClusterConfig.TheCurrentPageConfigurationHas',
                  defaultMessage: '当前页面配置已保存',
                })}
              >
                <Button
                  onClick={prevStep}
                  data-aspm-click="c307508.d317281"
                  data-aspm-desc={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.ClusterConfigurationPreviousStep',
                    defaultMessage: '集群配置-上一步',
                  })}
                  data-aspm-param={``}
                  data-aspm-expo
                >
                  {intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.PreviousStep',
                    defaultMessage: '上一步',
                  })}
                </Button>
              </Tooltip>
              <Button
                type="primary"
                onClick={nextStep}
                data-aspm-click="c307508.d317283"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.pages.components.ClusterConfig.ClusterConfigurationNextStep',
                  defaultMessage: '集群配置-下一步',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.pages.components.ClusterConfig.NextStep',
                  defaultMessage: '下一步',
                })}
              </Button>
            </Space>
          </div>
        </footer>
      </Space>
    </ProForm>
  );
}
