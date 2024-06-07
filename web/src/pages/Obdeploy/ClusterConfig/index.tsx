import InputPort from '@/component/InputPort';
import { PARAMETER_TYPE } from '@/constant/configuration';
import { queryComponentParameters } from '@/services/ob-deploy-web/Components';
import { getErrorInfo, serverReg } from '@/utils';
import {
  formatMoreConfig,
  generateRandomPassword,
  getPasswordRules,
} from '@/utils/helper';
import { intl } from '@/utils/intl';
import useRequest from '@/utils/useRequest';
import { QuestionCircleOutlined } from '@ant-design/icons';
import {
  ProCard,
  ProForm,
  ProFormRadio,
  ProFormText,
} from '@ant-design/pro-components';
import { useUpdateEffect } from 'ahooks';
import { Form, message, Row, Space, Switch, Tooltip } from 'antd';
import { useEffect, useState } from 'react';
import { getLocale, useModel } from 'umi';
import {
  commonStyle,
  configServerComponent,
  obagentComponent,
  obproxyComponent,
  ocpexpressComponent,
  onlyComponentsKeys,
  pathRule,
} from '../../constants';
import EnStyles from '../indexEn.less';
import ZhStyles from '../indexZh.less';
import TooltipInput from '../TooltipInput';
import type { RulesDetail } from './ConfigTable';
import ConfigTable, { parameterValidator } from './ConfigTable';
import Footer from './Footer';
import { getParamstersHandler } from './helper';
import Parameter from './Parameter';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

interface FormValues extends API.Components {
  oceanbase?: {
    mode?: string;
    parameters?: any;
  };
}

export default function ClusterConfig() {
  const {
    selectedConfig,
    setCurrentStep,
    configData,
    setConfigData,
    lowVersion,
    clusterMore,
    setClusterMore,
    componentsMore,
    setComponentsMore,
    clusterMoreConfig,
    setClusterMoreConfig,
    componentsMoreConfig,
    setComponentsMoreConfig,
    setErrorVisible,
    setErrorsList,
    errorsList,
    MODE_CONFIG_RULE,
  } = useModel('global');
  const { components = {}, home_path } = configData || {};
  const {
    oceanbase = {},
    ocpexpress = {},
    obproxy = {},
    obagent = {},
    obconfigserver = {},
  } = components;

  const [form] = ProForm.useForm();
  const proxyPasswordFormValue = ProForm.useWatch(
    ['obproxy', 'parameters', 'obproxy_sys_password', 'params'],
    form,
  );
  const authPasswordFormValue = ProForm.useWatch(
    ['obagent', 'parameters', 'http_basic_auth_password', 'params'],
    form,
  );
  const configserverAddressFormValue = ProForm.useWatch(
    ['obconfigserver', 'parameters', 'vip_address', 'params'],
    form,
  );
  const configserverPortFormValue = ProForm.useWatch(
    ['obconfigserver', 'parameters', 'vip_port', 'params'],
    form,
  );
  const [proxyParameterRules, setProxyParameterRules] = useState<RulesDetail>({
    rules: [() => ({ validator: parameterValidator })],
    targetTable: 'obproxy-ce',
    targetColumn: 'obproxy_sys_password',
  });
  const [authParameterRules, setAuthParameterRules] = useState<RulesDetail>({
    rules: [() => ({ validator: parameterValidator })],
    targetTable: 'obagent',
    targetColumn: 'http_basic_auth_password',
  });
  const [configserverAddressRules, setConfigserverAddressRules] =
    useState<RulesDetail>({
      rules: [],
      targetTable: 'ob-configserver',
      targetColumn: 'vip_address',
    });
  const [configserverPortRules, setConfigserverPortRules] =
    useState<RulesDetail>({
      rules: [],
      targetTable: 'ob-configserver',
      targetColumn: 'vip_port',
    });
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
    if (selectedConfig.includes(obproxyComponent)) {
      newComponents.obproxy = {
        ...(components.obproxy || {}),
        ...dataSource.obproxy,
        parameters: formatParameters(dataSource.obproxy?.parameters),
      };
    }
    if (selectedConfig.includes(ocpexpressComponent) && !lowVersion) {
      newComponents.ocpexpress = {
        ...(components.ocpexpress || {}),
        ...dataSource.ocpexpress,
        parameters: formatParameters(dataSource.ocpexpress?.parameters),
      };
    }
    if (selectedConfig.includes(obagentComponent)) {
      newComponents.obagent = {
        ...(components.obagent || {}),
        ...dataSource.obagent,
        parameters: formatParameters(dataSource.obagent?.parameters),
      };
    }
    if (selectedConfig.includes(configServerComponent)) {
      newComponents.obconfigserver = {
        ...(components.obconfigserver || {}),
        ...dataSource.obconfigserver,
        parameters: formatParameters(dataSource.obconfigserver?.parameters),
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
            type: item.type,
            isChanged: item.is_changed,
            unitDisable: item?.unitDisable,
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
        if (
          (parameter.params.type === PARAMETER_TYPE.capacity ||
            parameter.params.type === PARAMETER_TYPE.capacityMB) &&
          parameter.params.value == '0'
        ) {
          parameter.params.value += 'GB';
        }
        parameters[item.name] = parameter;
      });
      return parameters;
    } else {
      return undefined;
    }
  };

  const errorHandle = (e: any) => {
    setClusterMore(false);
    const errorInfo = getErrorInfo(e);
    setErrorVisible(true);
    setErrorsList([...errorsList, errorInfo]);
  };

  const getClusterMoreParamsters = async () => {
    setClusterMoreLoading(true);
    const res = await getParamstersHandler(
      getMoreParamsters,
      oceanbase,
      errorHandle,
    );

    if (res?.success) {
      const { data } = res,
        isSelectOcpexpress = selectedConfig.includes(ocpexpressComponent);
      const newClusterMoreConfig = formatMoreConfig(
        data?.items,
        isSelectOcpexpress,
      );

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
          obconfigserver: {
            parameters: getInitialParameters(
              obconfigserver?.component,
              obconfigserver.parameters,
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

  useEffect(() => {
    if (clusterMore) {
      getClusterMoreParamsters();
    }
    if (componentsMore) {
      getComponentsMoreParamsters();
    }
  }, []);

  useUpdateEffect(() => {
    if (!proxyPasswordFormValue?.adaptive) {
      setProxyParameterRules({
        rules: getPasswordRules('ob'),
        targetTable: 'obproxy-ce',
        targetColumn: 'obproxy_sys_password',
      });
    } else {
      setProxyParameterRules({
        rules: [() => ({ validator: parameterValidator })],
        targetTable: 'obproxy-ce',
        targetColumn: 'obproxy_sys_password',
      });
    }
  }, [proxyPasswordFormValue]);
  useUpdateEffect(() => {
    if (!authPasswordFormValue?.adaptive) {
      setAuthParameterRules({
        rules: getPasswordRules('ocp'),
        targetTable: 'obagent',
        targetColumn: 'http_basic_auth_password',
      });
    } else {
      setAuthParameterRules({
        rules: [() => ({ validator: parameterValidator })],
        targetTable: 'obagent',
        targetColumn: 'http_basic_auth_password',
      });
    }
  }, [authPasswordFormValue]);

  useUpdateEffect(() => {
    if (
      !configserverAddressFormValue?.adaptive ||
      !configserverPortFormValue?.adaptive
    ) {
      // ip和端口可以都为空或者都不为空
      if (
        configserverAddressFormValue?.value ||
        configserverPortFormValue?.value
      ) {
        setConfigserverAddressRules({
          rules: [
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.Obdeploy.ClusterConfig.PleaseEnter',
                defaultMessage: '请输入',
              }),
            },
            () => ({
              validator: (_: any, param?: API.ParameterValue) => {
                if (serverReg.test(param?.value || '')) {
                  return Promise.resolve();
                }
                return Promise.reject(
                  intl.formatMessage({
                    id: 'OBD.Obdeploy.ClusterConfig.TheIpAddressFormatIs',
                    defaultMessage: 'ip格式错误',
                  }),
                );
              },
            }),
          ],

          targetTable: 'ob-configserver',
          targetColumn: 'vip_address',
        });
        setConfigserverPortRules({
          rules: [
            () => ({
              validator: (_: any, param?: API.ParameterValue) => {
                if (!param?.value) {
                  return Promise.reject(
                    intl.formatMessage({
                      id: 'OBD.Obdeploy.ClusterConfig.PleaseEnter',
                      defaultMessage: '请输入',
                    }),
                  );
                }
                return Promise.resolve();
              },
            }),
          ],
          targetTable: 'ob-configserver',
          targetColumn: 'vip_port',
        });
      } else {
        setConfigserverAddressRules({
          rules: [],
          targetTable: 'ob-configserver',
          targetColumn: 'vip_address',
        });
        setConfigserverPortRules({
          rules: [],
          targetTable: 'ob-configserver',
          targetColumn: 'vip_port',
        });
        form.validateFields([
          ['obconfigserver', 'parameters', 'vip_address', 'params'],
          ['obconfigserver', 'parameters', 'vip_port', 'params'],
        ]);
      }
    }
  }, [configserverAddressFormValue, configserverPortFormValue]);

  const initPassword = generateRandomPassword('ob');

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
    obconfigserver: {
      listen_port: obconfigserver?.listen_port || 8080,
      parameters: getInitialParameters(
        obconfigserver?.component,
        obconfigserver?.parameters,
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
              href={MODE_CONFIG_RULE}
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
              validateFirst
              placeholder={intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.PleaseEnter',
                defaultMessage: '请输入',
              })}
              rules={getPasswordRules('ob')}
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
                <InputPort
                  name={['oceanbase', 'mysql_port']}
                  label={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.SqlPort',
                    defaultMessage: 'SQL 端口',
                  })}
                  fieldProps={{ style: commonStyle }}
                />

                <InputPort
                  name={['oceanbase', 'rpc_port']}
                  label={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.RpcPort',
                    defaultMessage: 'RPC 端口',
                  })}
                  fieldProps={{ style: commonStyle }}
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
            <ConfigTable
              showVisible={clusterMore}
              dataSource={clusterMoreConfig}
              loading={clusterMoreLoading}
              customParameter={<Parameter />}
            />
          </ProCard>
        </ProCard>
        {selectedConfig.length ? (
          <ProCard className={styles.pageCard} split="horizontal">
            <ProCard
              title={intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.ComponentConfiguration',
                defaultMessage: '组件配置',
              })}
              className="card-padding-bottom-24"
            >
              {selectedConfig.includes(obproxyComponent) && (
                <Row>
                  <Space size="middle">
                    <InputPort
                      name={['obproxy', 'listen_port']}
                      label={intl.formatMessage({
                        id: 'OBD.pages.components.ClusterConfig.ObproxyServicePort',
                        defaultMessage: 'OBProxy 服务端口',
                      })}
                      fieldProps={{ style: commonStyle }}
                    />

                    <InputPort
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
                    />
                  </Space>
                </Row>
              )}

              {selectedConfig.includes(obagentComponent) && (
                <Row>
                  <Space size="middle">
                    <InputPort
                      name={['obagent', 'monagent_http_port']}
                      label={intl.formatMessage({
                        id: 'OBD.pages.components.ClusterConfig.ObagentMonitoringServicePort',
                        defaultMessage: 'OBAgent 监控服务端口',
                      })}
                      fieldProps={{ style: commonStyle }}
                    />

                    <InputPort
                      name={['obagent', 'mgragent_http_port']}
                      label={intl.formatMessage({
                        id: 'OBD.pages.components.ClusterConfig.ObagentManageServicePorts',
                        defaultMessage: 'OBAgent 管理服务端口',
                      })}
                      fieldProps={{ style: commonStyle }}
                    />
                  </Space>
                </Row>
              )}

              {(selectedConfig.includes(ocpexpressComponent) ||
                selectedConfig.includes(configServerComponent)) &&
                !lowVersion && (
                  <Row>
                    <Space size="middle">
                      {selectedConfig.includes(ocpexpressComponent) && (
                        <InputPort
                          name={['ocpexpress', 'port']}
                          label={intl.formatMessage({
                            id: 'OBD.pages.components.ClusterConfig.PortOcpExpress',
                            defaultMessage: 'OCP Express 端口',
                          })}
                          fieldProps={{ style: commonStyle }}
                        />
                      )}

                      {selectedConfig.includes(configServerComponent) && (
                        <InputPort
                          name={['obconfigserver', 'listen_port']}
                          label={intl.formatMessage({
                            id: 'OBD.Obdeploy.ClusterConfig.ObconfigserverServicePort',
                            defaultMessage: 'OBConfigserver 服务端口',
                          })}
                          fieldProps={{ style: commonStyle }}
                        />
                      )}
                    </Space>
                  </Row>
                )}

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
              <ConfigTable
                showVisible={componentsMore}
                dataSource={componentsMoreConfig}
                loading={componentsMoreLoading}
                customParameter={<Parameter />}
                parameterRules={[
                  proxyParameterRules,
                  authParameterRules,
                  configserverAddressRules,
                  configserverPortRules,
                ]}
              />
            </ProCard>
          </ProCard>
        ) : null}
        <Footer prevStep={prevStep} nextStep={nextStep} />
      </Space>
    </ProForm>
  );
}
