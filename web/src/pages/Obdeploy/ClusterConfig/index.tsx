import ComponentsPort from '@/component/ComponentsPort';
import CustomPasswordInput from '@/component/CustomPasswordInput';
import InputPort from '@/component/InputPort';
import MoreConfigTable from '@/component/MoreConfigTable';
import type { MsgInfoType } from '@/component/OCPConfigNew';
import { queryComponentParameters } from '@/services/ob-deploy-web/Components';
import { getErrorInfo } from '@/utils';
import { formatMoreConfig, getInitialParameters } from '@/utils/helper';
import { intl } from '@/utils/intl';
import useRequest from '@/utils/useRequest';
import { ProCard, ProForm, ProFormRadio } from '@ant-design/pro-components';
import { Form, message, Row, Space, Switch } from 'antd';
import { useEffect, useState } from 'react';
import { getLocale, useModel } from 'umi';
import {
  commonInputStyle,
  commonPortStyle,
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
import ConfigTable from './ConfigTable';
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

export const formatParameters = (dataSource: any) => {
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
  const [currentMode, setCurrentMode] = useState(
    oceanbase?.mode || 'PRODUCTION',
  );

  const [passwordVisible, setPasswordVisible] = useState(true);
  // const [adminPasswdVisible, setAdminPasswdVisible] = useState(true);
  const [clusterMoreLoading, setClusterMoreLoading] = useState(false);
  const [componentsMoreLoading, setComponentsMoreLoading] = useState(false);
  const [obRootPwd, setRootPwd] = useState<string>(
    oceanbase?.root_password || '',
  );
  const [ocpExpressPwd, setOcpExpressPwd] = useState<string>(
    ocpexpress?.admin_passwd || '',
  );
  const [obPwdMsgInfo, setObPwdMsgInfo] = useState<MsgInfoType>();
  const [ocpPwdMsgInfo, setOcpPwdMsgInfo] = useState<MsgInfoType>();
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

  const obRootPwdChange = (password: string) => {
    form.setFieldValue(['oceanbase', 'root_password'], password);
    form.validateFields([['oceanbase', 'root_password']]);
    setRootPwd(password);
  };

  const ocpexpressPwdChange = (password: string) => {
    form.setFieldValue(['ocpexpress', 'admin_passwd'], password);
    form.validateFields([['ocpexpress', 'admin_passwd']]);
    setOcpExpressPwd(password);
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
        if (errorName?.includes('parameters')) {
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
  }, [clusterMore]);

  useEffect(() => {
    if (componentsMore) {
      getComponentsMoreParamsters();
    }
  }, [componentsMore]);

  const initialValues = {
    oceanbase: {
      mode: oceanbase?.mode || 'PRODUCTION',
      root_password: oceanbase?.root_password,
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
      rpc_listen_port: obproxy?.rpc_listen_port || 2885,
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
      admin_passwd: ocpexpress?.admin_passwd,
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
            <CustomPasswordInput
              msgInfo={obPwdMsgInfo}
              setMsgInfo={setObPwdMsgInfo}
              form={form}
              onChange={obRootPwdChange}
              useFor="ob"
              value={obRootPwd}
              name={['oceanbase', 'root_password']}
              label={intl.formatMessage({
                id: 'OBD.pages.components.ClusterConfig.RootSysPassword',
                defaultMessage: 'root@sys 密码',
              })}
              style={{ height: 86, ...commonInputStyle }}
              innerInputStyle={{ width: 388 }}
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
                  <TooltipInput
                    fieldProps={{ style: commonInputStyle }}
                    placeholder={initDir}
                    name="data_dir"
                  />
                </Form.Item>
                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.LogDirectory',
                    defaultMessage: '日志目录',
                  })}
                  name={['oceanbase', 'redo_dir']}
                  rules={[pathRule]}
                >
                  <TooltipInput
                    fieldProps={{ style: commonInputStyle }}
                    placeholder={initDir}
                    name="redo_dir"
                  />
                </Form.Item>
              </Space>
            </Row>
            <Row>
              <Space size="large">
                <InputPort
                  name={['oceanbase', 'mysql_port']}
                  label={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.SqlPort',
                    defaultMessage: 'SQL 端口',
                  })}
                  fieldProps={{ style: commonPortStyle }}
                />

                <InputPort
                  name={['oceanbase', 'rpc_port']}
                  label={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.RpcPort',
                    defaultMessage: 'RPC 端口',
                  })}
                  fieldProps={{ style: commonPortStyle }}
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
              {selectedConfig.includes('ocp-express') && !lowVersion && (
                <CustomPasswordInput
                  msgInfo={ocpPwdMsgInfo}
                  setMsgInfo={setOcpPwdMsgInfo}
                  form={form}
                  onChange={ocpexpressPwdChange}
                  useFor="ocp"
                  useOldRuler={true}
                  value={ocpExpressPwd}
                  name={['ocpexpress', 'admin_passwd']}
                  label={intl.formatMessage({
                    id: 'OBD.Obdeploy.ClusterConfig.OcpExpressAdministratorPassword',
                    defaultMessage: 'OCP Express 管理员密码',
                  })}
                  innerInputStyle={{ width: 388 }}
                  style={{ height: 86, ...commonInputStyle }}
                />
              )}
              <ComponentsPort
                lowVersion={lowVersion}
                selectedConfig={selectedConfig}
              />
              <MoreConfigTable
                loading={componentsMoreLoading}
                datasource={componentsMoreConfig}
                switchChecked={componentsMore}
                switchOnChange={handleComponentsMoreChange}
                form={form}
              />
            </ProCard>
          </ProCard>
        ) : null}
        <Footer prevStep={prevStep} nextStep={nextStep} />
      </Space>
    </ProForm>
  );
}
