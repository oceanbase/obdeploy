import ComponentsPort from '@/component/ComponentsPort';
import CustomFooter from '@/component/CustomFooter';
import MoreConfigTable from '@/component/MoreConfigTable';
import { queryComponentParameters } from '@/services/ob-deploy-web/Components';
import { getErrorInfo, handleQuit, PASSWORD_REGEX, serversValidator, validatePassword } from '@/utils';
import { formatMoreConfig, getInitialParameters } from '@/utils/helper';
import { intl } from '@/utils/intl';
import useRequest from '@/utils/useRequest';
import { InfoCircleFilled } from '@ant-design/icons';
import {
  EditableFormInstance,
  ProCard,
  ProForm,
  ProFormSelect,
  ProFormText,
} from '@ant-design/pro-components';
import { Button, Space, Row, Col, Form } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { getLocale, useModel } from 'umi';
import {
  configServerComponent,
  grafanaComponent,
  obagentComponent,
  onlyComponentsKeys,
  pathRule,
  prometheusComponent,
  alertManagerComponent,
} from '../constants';
import { formatParameters } from '../Obdeploy/ClusterConfig';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';
import { Password } from '@oceanbase/ui';
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
    obproxy = {},
    obagent = {},
    obconfigserver = {},
    appname,
    home_path,
    grafana = {},
    prometheus = {},
    alertmanager = {},
  } = componentConfig;
  const components = { prometheus, obproxy, obagent, obconfigserver, grafana, alertmanager };
  const { setErrorVisible, setErrorsList, errorsList, handleQuitProgress } =
    useModel('global');
  const homePathSuffix = `/${appname}`;
  const [componentsMoreLoading, setComponentsMoreLoading] = useState(false);
  const [grafanaPassed, setGrafanaPassed] = useState<boolean>(true);
  const [prometheusPassed, setPrometheusPassed] = useState<boolean>(true);
  const [alertmanagerPassed, setAlertmanagerPassed] = useState<boolean>(true);
  const [prometheusPwd, setPrometheusPwd] = useState<string>(
    prometheus?.basic_auth_users?.admin || '',
  );
  const [alertmanagerPwd, setAlertmanagerPwd] = useState<string>(
    alertmanager?.basic_auth_users?.admin || '',
  );
  const [grafanaPwd, setGrafanaPwd] = useState<string>(
    grafana?.login_password || '',
  );

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
    grafana: {
      port: grafana?.port || 3000,
      servers: grafana?.servers,
      parameters: getInitialParameters(
        grafana?.component,
        grafana?.parameters,
        componentsMoreConfig,
      ),
    },
    prometheus: {
      port: prometheus?.port || 9090,
      servers: prometheus?.servers,
      parameters: getInitialParameters(
        prometheus?.component,
        prometheus?.parameters,
        componentsMoreConfig,
      ),
    },
    alertmanager: {
      port: alertmanager?.port || 9093,
      servers: alertmanager?.servers,
      parameters: getInitialParameters(
        alertmanager?.component,
        alertmanager?.parameters,
        componentsMoreConfig,
      ),
    },
    home_path: initHomePath,
  };

  const tableFormRef = useRef<EditableFormInstance<API.DBConfig>>();
  const [alertmanagerValues, setAlertmanagerValues] = useState<string[]>([]);

  if (!lowVersion) {
  }

  const prometheusPwdChange = (password: string) => {
    form.setFieldValue(['prometheus', 'basic_auth_users', 'admin'], password);
    form.validateFields([['prometheus', 'basic_auth_users', 'admin']]);
    setPrometheusPwd(password);
  };
  const alertmanagerPwdChange = (password: string) => {
    form.setFieldValue(['alertmanager', 'basic_auth_users', 'admin'], password);
    form.validateFields([['alertmanager', 'basic_auth_users', 'admin']]);
    setAlertmanagerPwd(password);
  };
  const grafanaPwdChange = (password: string) => {
    form.setFieldValue(['grafana', 'login_password'], password);
    form.validateFields([['grafana', 'login_password']]);
    setGrafanaPwd(password);
  };

  const getComponentsMoreParamsters = async () => {
    const filters: API.ParameterFilter[] = [];
    let currentOnlyComponentsKeys: string[] = onlyComponentsKeys;
    if (lowVersion) {
      currentOnlyComponentsKeys = onlyComponentsKeys.filter(
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
    if (selectedConfig.includes(obagentComponent)) {
      newComponents.obagent = {
        ...(components.obagent || {}),
        ...dataSource?.obagent,
        parameters: formatParameters(dataSource.obagent?.parameters),
        component: obagentComponent,
        // 确保版本信息被保留
        version: components.obagent?.version || obagentComponent,
        release: components.obagent?.release,
        package_hash: components.obagent?.package_hash,
      };
    }
    if (selectedConfig.includes(configServerComponent)) {
      newComponents.obconfigserver = {
        ...(components.obconfigserver || {}),
        ...dataSource?.obconfigserver,
        parameters: formatParameters(dataSource.obconfigserver?.parameters),
      };
    }
    if (selectedConfig.includes(grafanaComponent)) {
      newComponents.grafana = {
        ...(components?.grafana || {}),
        ...dataSource.grafana,
        parameters: formatParameters(dataSource.grafana?.parameters),
        component: grafanaComponent,
        // 确保版本信息被保留
        version: components?.grafana?.version,
        release: components?.grafana?.release,
        package_hash: components?.grafana?.package_hash,
      };
    }
    if (selectedConfig.includes(prometheusComponent)) {
      newComponents.prometheus = {
        ...(components?.prometheus || {}),
        ...dataSource.prometheus,
        parameters: formatParameters(dataSource.prometheus?.parameters),
        component: prometheusComponent,
        // 确保版本信息被保留
        version: components?.prometheus?.version,
        release: components?.prometheus?.release,
        package_hash: components?.prometheus?.package_hash,
      };
    }
    if (selectedConfig.includes(alertManagerComponent)) {
      newComponents.alertmanager = {
        ...(components?.alertmanager || {}),
        ...dataSource.alertmanager,
        parameters: formatParameters(dataSource.alertmanager?.parameters),
        component: alertManagerComponent,
        // 确保版本信息被保留
        version: components?.alertmanager?.version,
        release: components?.alertmanager?.release,
        package_hash: components?.alertmanager?.package_hash,
      };
    }
    setComponentConfig({
      ...componentConfig,
      ...newComponents,
      home_path: `${dataSource.home_path}${homePathSuffix}`,
      deployUser: dataSource.deployUser,
    });
  };

  useEffect(() => {
    if (alertmanager?.servers && Array.isArray(alertmanager.servers) && alertmanager.servers.length > 0) {
      setAlertmanagerValues(alertmanager.servers);
    }
  }, [alertmanager?.servers]);

  const nextStep = () => {
    // 在验证前，确保 alertmanager 的值只包含当前显示的那个值
    if (alertmanagerValues.length > 0) {
      form.setFieldValue(['alertmanager', 'servers'], alertmanagerValues);
      if (tableFormRef.current) {
        tableFormRef.current.setFieldValue(['alertmanager', 'servers'], alertmanagerValues);
      }
    }
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

  // 手动设置端口初始值
  useEffect(() => {
    if (selectedConfig.includes(prometheusComponent)) {
      form.setFieldValue(['prometheus', 'port'], 9090);
    }
    if (selectedConfig.includes(grafanaComponent)) {
      form.setFieldValue(['grafana', 'port'], 3000);
    }
    if (selectedConfig.includes(alertManagerComponent)) {
      form.setFieldValue(['alertmanager', 'port'], 9093);
    }
  }, [selectedConfig, form]);

  return (
    <ProForm
      form={form}
      submitter={false}
      initialValues={initialValues}
      validateTrigger={['onBlur', 'onChange']}
    >
      <Space className={styles.spaceWidth} direction="vertical" size="middle">
        {selectedConfig?.includes('obproxy-ce') ||
          selectedConfig?.includes(configServerComponent) ||
          selectedConfig?.includes(grafanaComponent) ||
          selectedConfig?.includes(prometheusComponent) ||
          selectedConfig?.includes(alertManagerComponent) ? (
          <ProCard
            className={styles.pageCard}
            bodyStyle={{ paddingBottom: 0 }}
            title={intl.formatMessage({
              id: 'OBD.pages.ComponentDeploy.ComponentConfig.ComponentNodeConfiguration',
              defaultMessage: '组件节点配置',
            })}
          >
            <Row>
              {selectedConfig?.includes('obproxy-ce') ? (
                <Col span={8} >
                  <ProFormSelect
                    name={['obproxy', 'servers']}
                    label={intl.formatMessage({
                      id: 'OBD.pages.ComponentDeploy.ComponentConfig.ObproxyNodes',
                      defaultMessage: 'OBProxy 节点',
                    })}
                    placeholder="请选择或输入 OBProxy 节点"
                    mode="tags"
                    rules={[
                      {
                        validator: (_: any, value: string[]) =>
                          serversValidator(_, value, 'OBProxy'),
                      },
                    ]}
                    fieldProps={{
                      style: commonWidth,
                    }}
                  />
                </Col>
              ) : null}
              {selectedConfig?.includes(configServerComponent) ? (
                <Col span={8}>
                  <ProFormSelect
                    name={['obconfigserver', 'servers']}
                    label={intl.formatMessage({
                      id: 'OBD.pages.ComponentDeploy.ComponentConfig.ObconfigserverNodes',
                      defaultMessage: 'obconfigserver 节点',
                    })}
                    placeholder="请选择或输入 OBConfigServer 节点"
                    mode="tags"
                    rules={[
                      {
                        validator: (_: any, value: string[]) =>
                          serversValidator(_, value, 'OBConfigServer'),
                      },
                    ]}
                    fieldProps={{
                      style: commonWidth,
                    }}
                  />
                </Col>
              ) : null}
              {selectedConfig?.includes(grafanaComponent) ? (
                <Col span={8}>
                  <ProFormSelect
                    name={['grafana', 'servers']}
                    label={'Grafana 节点'}
                    placeholder="请选择或输入 Grafana 节点"
                    mode="tags"
                    rules={[
                      {
                        validator: (_: any, value: string[]) =>
                          serversValidator(_, value, 'Grafana'),
                      },
                    ]}
                    fieldProps={{
                      style: commonWidth,
                    }}
                  />
                </Col>
              ) : null}
              {selectedConfig?.includes(prometheusComponent) ? (
                <Col span={8}>
                  <ProFormSelect
                    name={['prometheus', 'servers']}
                    label={'Prometheus 节点'}
                    placeholder="请选择或输入 Prometheus 节点"
                    mode="tags"
                    rules={[
                      {
                        validator: (_: any, value: string[]) =>
                          serversValidator(_, value, 'Prometheus'),
                      },
                    ]}
                    fieldProps={{
                      style: commonWidth,
                    }}
                  />
                </Col>
              ) : null}
              {selectedConfig?.includes(alertManagerComponent) ? (
                <Col span={8}>
                  <ProFormSelect
                    name={['alertmanager', 'servers']}
                    label={'AlertManager 节点'}
                    mode="tags"
                    placeholder="请选择或输入 AlertManager 节点"
                    rules={[
                      {
                        validator: (_: any, value: string[]) =>
                          serversValidator(_, value, 'AlertManager'),
                      },
                    ]}
                    fieldProps={{
                      style: commonWidth,
                      value: alertmanagerValues,
                      onSelect: (value: any) => {
                        // 强制只保留一个值
                        setAlertmanagerValues([value]);
                      },
                      onDeselect: (value: any) => {
                        // 允许删除值，清空选择
                        setAlertmanagerValues([]);
                      },
                    }}
                  />
                </Col>
              ) : null}
            </Row>
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
              {selectedConfig.includes(grafanaComponent) && (
                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.DKFFMK27',
                    defaultMessage: 'Grafana 密码',
                  })}
                  name={['grafana', 'login_password']}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.pages.components.ClusterConfig.DKFFMK28',
                        defaultMessage: '请输入或随机生成 Grafana 密码',
                      }),
                    },
                    {
                      validator: validatePassword(grafanaPassed),
                    },
                  ]}
                  initialValue={grafanaPwd}
                >
                  <Password
                    generatePasswordRegex={PASSWORD_REGEX}
                    onValidate={(value) => {
                      setGrafanaPassed(value);
                    }}
                    style={{ width: 388, borderColor: '#CDD5E4' }}
                    onChange={grafanaPwdChange}
                  />
                </Form.Item>
              )}
              {selectedConfig.includes(prometheusComponent) && (
                <Form.Item
                  label={intl.formatMessage({
                    id: 'OBD.pages.components.ClusterConfig.DKFFMK29',
                    defaultMessage: 'Prometheus 密码',
                  })}
                  name={['prometheus', 'basic_auth_users', 'admin']}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.pages.components.ClusterConfig.DKFFMK26',
                        defaultMessage: '请输入或随机生成 Prometheus 密码',
                      }),
                    },
                    {
                      validator: validatePassword(prometheusPassed),
                    },
                  ]}
                  initialValue={prometheusPwd}
                >
                  <Password
                    generatePasswordRegex={PASSWORD_REGEX}
                    onValidate={(value) => {
                      setPrometheusPassed(value);
                    }}
                    style={{ width: 388, borderColor: '#CDD5E4' }}
                    onChange={prometheusPwdChange}
                  />
                </Form.Item>
              )}
              {selectedConfig.includes(alertManagerComponent) && (
                <Form.Item
                  label={'AlertManager 密码'}
                  name={['alertmanager', 'basic_auth_users', 'admin']}
                  rules={[
                    {
                      required: true,
                      message: intl.formatMessage({
                        id: 'OBD.pages.components.ClusterConfig.DKFFMK26',
                        defaultMessage: '请输入或随机生成 AlertManager 密码',
                      }),
                    },
                    {
                      validator: validatePassword(alertmanagerPassed),
                    },
                  ]}
                  initialValue={alertmanagerPwd}
                >
                  <Password
                    generatePasswordRegex={PASSWORD_REGEX}
                    onValidate={(value) => {
                      setAlertmanagerPassed(value);
                    }}
                    style={{ width: 388, borderColor: '#CDD5E4' }}
                    onChange={alertmanagerPwdChange}
                  />
                </Form.Item>
              )}

              <ComponentsPort
                form={form}
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
        <Button
          onClick={() => handleQuit(handleQuitProgress, setCurrent, false, 5)}
        >
          {intl.formatMessage({
            id: 'OBD.pages.ComponentDeploy.ComponentConfig.Exit',
            defaultMessage: '退出',
          })}
        </Button>
      </CustomFooter>
    </ProForm>
  );
}
