import ComponentsPort from '@/component/ComponentsPort';
import CustomFooter from '@/component/CustomFooter';
import MoreConfigTable from '@/component/MoreConfigTable';
import { queryComponentParameters } from '@/services/ob-deploy-web/Components';
import { getErrorInfo, handleQuit, serversValidator } from '@/utils';
import { formatMoreConfig, getInitialParameters } from '@/utils/helper';
import { intl } from '@/utils/intl';
import useRequest from '@/utils/useRequest';
import { InfoCircleFilled } from '@ant-design/icons';
import {
  ProCard,
  ProForm,
  ProFormSelect,
  ProFormText,
} from '@ant-design/pro-components';
import { Button, Space } from 'antd';
import { useEffect, useState } from 'react';
import { getLocale, useModel } from 'umi';
import {
  configServerComponent,
  obagentComponent,
  ocpexpressComponent,
  onlyComponentsKeys,
  pathRule,
} from '../constants';
import { formatParameters } from '../Obdeploy/ClusterConfig';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';
const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

const commonWidth = { width: 314 };

export const DeployedUserTitle = () => (
  <div>
    <span>
      {intl.formatMessage({
        id: 'OBD.pages.ComponentDeploy.ComponentConfig.DeployUsers',
        defaultMessage: '部署用户',
      })}
    </span>
    <InfoCircleFilled
      style={{ color: '#006aff', marginLeft: 17, marginRight: 5 }}
    />

    <span style={{ color: '#8592ad', fontSize: 14, fontWeight: 400 }}>
      {intl.formatMessage({
        id: 'OBD.pages.ComponentDeploy.ComponentConfig.EnsureThatTheDeploymentUser',
        defaultMessage: '请保障部署用户已在各主机上存在并赋予对应目录权限',
      })}
    </span>
  </div>
);

interface FormValues extends API.Components {
  deployUser: string;
  home_path: string;
}

export default function ComponentConfig() {
  const [form] = ProForm.useForm();
  const {
    selectedConfig,
    deployUser,
    setCurrent,
    current,
    componentsMore,
    setComponentsMore,
    componentsMoreConfig,
    setComponentsMoreConfig,
    lowVersion,
    componentConfig,
    setComponentConfig,
  } = useModel('componentDeploy');
  const {
    ocpexpress = {},
    obproxy = {},
    obagent = {},
    obconfigserver = {},
    appname,
    home_path,
  } = componentConfig;
  const components = { ocpexpress, obproxy, obagent, obconfigserver };
  const { setErrorVisible, setErrorsList, errorsList, handleQuitProgress } =
    useModel('global');
  const homePathSuffix = `/${appname}`;
  const [componentsMoreLoading, setComponentsMoreLoading] = useState(false);
  const [ocpServerDropdownVisible, setOcpServerDropdownVisible] =
    useState<boolean>(false);

  const { run: getMoreParamsters } = useRequest(queryComponentParameters);
  const newDeployUser =
    deployUser === 'root' ? `/${deployUser}` : `/home/${deployUser}`;

  const initHomePath = home_path
    ? home_path.substring(0, home_path.length - homePathSuffix.length)
    : newDeployUser;
  const initialValues = {
    deployUser,
    obproxy: {
      listen_port: obproxy?.listen_port || 2883,
      prometheus_listen_port: obproxy?.prometheus_listen_port || 2884,
      rpc_listen_port: obproxy?.rpc_listen_port || 2885,
      servers: obproxy?.servers,
      parameters: getInitialParameters(
        obproxy?.component,
        obproxy?.parameters,
        componentsMoreConfig,
      ),
    },
    obagent: {
      monagent_http_port: obagent?.monagent_http_port || 8088,
      mgragent_http_port: obagent?.mgragent_http_port || 8089,
      servers: obagent?.servers,
      parameters: getInitialParameters(
        obagent?.component,
        obagent?.parameters,
        componentsMoreConfig,
      ),
    },
    obconfigserver: {
      listen_port: obconfigserver?.listen_port || 8080,
      servers: obconfigserver?.servers,
      parameters: getInitialParameters(
        obconfigserver?.component,
        obconfigserver?.parameters,
        componentsMoreConfig,
      ),
    },
    home_path: initHomePath,
  };
  if (!lowVersion) {
    initialValues.ocpexpress = {
      port: ocpexpress?.port || 8180,
      servers: ocpexpress?.servers,
      parameters: getInitialParameters(
        ocpexpress?.component,
        ocpexpress?.parameters,
        componentsMoreConfig,
      ),
    };
  }
  const getComponentsMoreParamsters = async () => {
    const filters: API.ParameterFilter[] = [];
    let currentOnlyComponentsKeys: string[] = onlyComponentsKeys;
    if (lowVersion) {
      currentOnlyComponentsKeys = onlyComponentsKeys.filter(
        (key) => key !== 'ocpexpress',
      );
    }
    currentOnlyComponentsKeys.forEach((item) => {
      if (components[item]?.component && components[item]?.version) {
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
  const handleComponentsMoreChange = (checked: boolean) => {
    setComponentsMore(checked);
    if (!componentsMoreConfig?.length) {
      getComponentsMoreParamsters();
    }
  };
  const setData = (dataSource: FormValues) => {
    let newComponents: API.Components = {};
    if (selectedConfig.includes('obproxy-ce')) {
      newComponents.obproxy = {
        ...(components.obproxy || {}),
        ...dataSource?.obproxy,
        parameters: formatParameters(dataSource.obproxy?.parameters),
      };
    }
    if (selectedConfig.includes(ocpexpressComponent) && !lowVersion) {
      newComponents.ocpexpress = {
        ...(components.ocpexpress || {}),
        ...dataSource?.ocpexpress,
        parameters: formatParameters(dataSource.ocpexpress?.parameters),
      };
    }
    if (selectedConfig.includes(obagentComponent)) {
      newComponents.obagent = {
        ...(components.obagent || {}),
        ...dataSource?.obagent,
        parameters: formatParameters(dataSource.obagent?.parameters),
      };
    }
    if (selectedConfig.includes(configServerComponent)) {
      newComponents.obconfigserver = {
        ...(components.obconfigserver || {}),
        ...dataSource?.obconfigserver,
        parameters: formatParameters(dataSource.obconfigserver?.parameters),
      };
    }
    setComponentConfig({
      ...componentConfig,
      ...newComponents,
      home_path: `${dataSource.home_path}${homePathSuffix}`,
      deployUser: dataSource.deployUser,
    });
  };
  const nextStep = () => {
    form.validateFields().then((values) => {
      setData(values);
      setCurrent(current + 1);
      setErrorVisible(false);
      setErrorsList([]);
      window.scrollTo(0, 0);
    });
  };
  const preStep = () => {
    const formValues = form.getFieldsValue(true);
    setData(formValues);
    setCurrent(current - 1);
    setErrorVisible(false);
    setErrorsList([]);
    window.scrollTo(0, 0);
  };

  useEffect(() => {
    if (componentsMore) {
      getComponentsMoreParamsters();
    }
  }, [componentsMore]);
  return (
    <ProForm
      form={form}
      submitter={false}
      initialValues={initialValues}
      grid={true}
      validateTrigger={['onBlur', 'onChange']}
    >
      <Space className={styles.spaceWidth} direction="vertical" size="middle">
        {selectedConfig.includes('obproxy-ce') ||
        selectedConfig.includes(ocpexpressComponent) ||
        selectedConfig.includes(configServerComponent) ? (
          <ProCard
            className={styles.pageCard}
            bodyStyle={{ paddingBottom: 0 }}
            title={intl.formatMessage({
              id: 'OBD.pages.ComponentDeploy.ComponentConfig.ComponentNodeConfiguration',
              defaultMessage: '组件节点配置',
            })}
          >
            <Space size={24}>
              {selectedConfig.includes('obproxy-ce') ? (
                <ProFormSelect
                  name={['obproxy', 'servers']}
                  label={intl.formatMessage({
                    id: 'OBD.pages.ComponentDeploy.ComponentConfig.ObproxyNodes',
                    defaultMessage: 'OBProxy 节点',
                  })}
                  mode="tags"
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.pages.components.NodeConfig.SelectOrEnterObproxyNodes',
                        defaultMessage: '请选择或输入 OBProxy 节点',
                      }),
                    },
                    {
                      validator: (_: any, value: string[]) =>
                        serversValidator(_, value, 'OBProxy'),
                    },
                  ]}
                  fieldProps={{
                    style: commonWidth,
                  }}
                />
              ) : null}
              {selectedConfig.includes(ocpexpressComponent) ? (
                <ProFormSelect
                  name={['ocpexpress', 'servers']}
                  label={intl.formatMessage({
                    id: 'OBD.pages.ComponentDeploy.ComponentConfig.OcpExpressNodes',
                    defaultMessage: 'OCP Express 节点',
                  })}
                  mode="tags"
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.pages.ComponentDeploy.ComponentConfig.SelectOrEnterOcpExpress',
                        defaultMessage: '请选择或输入 OCP Express 节点',
                      }),
                    },
                    {
                      validator: (_: any, value: string[]) =>
                        serversValidator(_, value, 'OBServer'),
                    },
                  ]}
                  fieldProps={{
                    style: commonWidth,
                    open: ocpServerDropdownVisible,
                    onChange: (value) => {
                      if (value?.length) {
                        form.setFieldsValue({
                          ocpexpress: {
                            servers: [value[value.length - 1]],
                          },
                        });
                      }
                      setOcpServerDropdownVisible(false);
                    },
                    onFocus: () => setOcpServerDropdownVisible(true),
                    onClick: () =>
                      setOcpServerDropdownVisible(!ocpServerDropdownVisible),
                    onBlur: () => setOcpServerDropdownVisible(false),
                  }}
                />
              ) : null}
              {selectedConfig.includes(configServerComponent) ? (
                <ProFormSelect
                  name={['obconfigserver', 'servers']}
                  label={intl.formatMessage({
                    id: 'OBD.pages.ComponentDeploy.ComponentConfig.ObconfigserverNodes',
                    defaultMessage: 'obconfigserver 节点',
                  })}
                  mode="tags"
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.pages.Obdeploy.NodeConfig.SelectOrEnterObConfigserver',
                        defaultMessage: '请选择或输入 OB ConfigServer 节点',
                      }),
                    },
                    {
                      validator: (_: any, value: string[]) =>
                        serversValidator(_, value, 'obconfigserver'),
                    },
                  ]}
                  fieldProps={{
                    style: commonWidth,
                  }}
                />
              ) : null}
            </Space>
          </ProCard>
        ) : null}

        <ProCard
          bodyStyle={{ paddingBottom: 0 }}
          className={styles.pageCard}
          title={<DeployedUserTitle />}
        >
          <ProFormText
            label={intl.formatMessage({
              id: 'OBD.pages.ComponentDeploy.ComponentConfig.Username',
              defaultMessage: '用户名',
            })}
            disabled
            name={'deployUser'}
            fieldProps={{
              style: commonWidth,
            }}
          />
        </ProCard>
        <ProCard
          className={styles.pageCard}
          bodyStyle={{ paddingBottom: 0 }}
          title={intl.formatMessage({
            id: 'OBD.pages.ComponentDeploy.ComponentConfig.SoftwarePathConfiguration',
            defaultMessage: '软件路径配置',
          })}
        >
          <ProFormText
            fieldProps={{
              style: { width: 552 },
              addonAfter: homePathSuffix,
            }}
            rules={[
              {
                required: true,
                message: intl.formatMessage({
                  id: 'OBD.pages.ComponentDeploy.ComponentConfig.PleaseEnter',
                  defaultMessage: '请输入',
                }),
              },
              pathRule,
            ]}
            name={'home_path'}
            label={intl.formatMessage({
              id: 'OBD.pages.ComponentDeploy.ComponentConfig.SoftwarePath',
              defaultMessage: '软件路径',
            })}
            placeholder={intl.formatMessage({
              id: 'OBD.pages.ComponentDeploy.ComponentConfig.HomeStartUser',
              defaultMessage: '/home/启动用户',
            })}
          />
        </ProCard>
        {selectedConfig.length ? (
          <ProCard className={styles.pageCard} split="horizontal">
            <ProCard
              title={intl.formatMessage({
                id: 'OBD.pages.ComponentDeploy.ComponentConfig.ComponentConfiguration',
                defaultMessage: '组件配置',
              })}
              className="card-padding-bottom-24"
            >
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
      </Space>
      <CustomFooter>
        <Button
          onClick={() => handleQuit(handleQuitProgress, setCurrent, false, 5)}
        >
          {intl.formatMessage({
            id: 'OBD.pages.ComponentDeploy.ComponentConfig.Exit',
            defaultMessage: '退出',
          })}
        </Button>
        <Button onClick={preStep}>
          {intl.formatMessage({
            id: 'OBD.pages.ComponentDeploy.ComponentConfig.PreviousStep',
            defaultMessage: '上一步',
          })}
        </Button>
        <Button onClick={nextStep} type="primary">
          {intl.formatMessage({
            id: 'OBD.pages.ComponentDeploy.ComponentConfig.NextStep',
            defaultMessage: '下一步',
          })}
        </Button>
      </CustomFooter>
    </ProForm>
  );
}
