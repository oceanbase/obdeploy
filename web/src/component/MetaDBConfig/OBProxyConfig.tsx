import { intl } from '@/utils/intl';
import { ProCard, ProForm, ProFormSelect } from '@ant-design/pro-components';
import { useState } from 'react';
import { RightOutlined, DownOutlined } from '@ant-design/icons';
import { FormInstance } from 'antd/lib/form';
import { Row, Input, Space } from 'antd';
import { useModel } from 'umi';

import useRequest from '@/utils/useRequest';
import styles from './indexZh.less';
import { getErrorInfo } from '@/utils';
import Parameter from '@/pages/Obdeploy/ClusterConfig/Parameter';
import { queryComponentParameters } from '@/services/ob-deploy-web/Components';
import ConfigTable from '@/pages/Obdeploy/ClusterConfig/ConfigTable';
import InputPort from '../InputPort';
import { componentsConfig } from '@/pages/constants';
import { ocpServersValidator } from '@/utils';
import { showConfigKeys } from '@/constant/configuration';
import { componentVersionTypeToComponent } from '@/pages/constants';
import { obproxyAddonAfter } from '@/constant/configuration';
export default function OBProxyConfig({ form }: { form: FormInstance<any> }) {
  const {
    ocpConfigData,
    proxyMoreConfig,
    setProxyMoreConfig,
    setErrorVisible,
    setErrorsList,
    errorsList,
  } = useModel('global');
  const { isShowMoreConfig, setIsShowMoreConfig } = useModel('ocpInstallData');
  const { components = {} } = ocpConfigData || {};
  const { obproxy = {} } = components;
  const [proxyMoreLoading, setProxyMoreLoading] = useState(false);
  const { run: getMoreParamsters } = useRequest(queryComponentParameters);
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
          (parameter.params.type === 'CapacityMB' ||
            parameter.params.type === 'Capacity') &&
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
      result.configParameter.forEach((item) => {
        Object.assign(item.parameterValue, { type: item.type });
      });
      return result;
    });
  };
  const getProxyMoreParamsters = async () => {
    setProxyMoreLoading(true);
    try {
      const { success, data } = await getMoreParamsters(
        {},
        {
          filters: [
            {
              component: obproxy?.component,
              version: obproxy?.version,
              is_essential_only: true,
            },
          ],
        },
      );
      if (success) {
        const newClusterMoreConfig = formatMoreConfig(data?.items);
        setProxyMoreConfig(newClusterMoreConfig);
        form.setFieldsValue({
          obproxy: {
            parameters: getInitialParameters(
              obproxy?.component,
              obproxy?.parameters,
              newClusterMoreConfig,
            ),
          },
        });
      }
    } catch (e: any) {
      // aaa TypeError: Cannot read properties of undefined (reading 'setFieldsValue')
      setIsShowMoreConfig(false);
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    }
    setProxyMoreLoading(false);
  };

  const handleCluserMoreChange = () => {
    setIsShowMoreConfig(!isShowMoreConfig);
    if (!proxyMoreConfig?.length) {
      getProxyMoreParamsters();
    }
  };
  return (
    <ProCard
      title={intl.formatMessage({
        id: 'OBD.component.MetaDBConfig.OBProxyConfig.ObproxyConfiguration',
        defaultMessage: 'OBProxy 配置',
      })}
    >
      <ProFormSelect
        style={{ width: 201 }}
        mode="tags"
        name={['obproxy', 'servers']}
        rules={[
          {
            required: true,
            message: intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.OBProxyConfig.PleaseEnter',
              defaultMessage: '请输入',
            }),
          },
          {
            validator: ocpServersValidator,
            validateTrigger: 'onBlur',
          },
        ]}
        label={intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.OBProxyConfig.ObproxyNodes',
          defaultMessage: 'OBProxy 节点',
        })}
      />

      <Row>
        <Space size="middle">
          <InputPort
            name={['obproxy', 'listen_port']}
            label={intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.OBProxyConfig.SqlPort',
              defaultMessage: 'SQL 端口',
            })}
          />
          <InputPort
            name={['obproxy', 'prometheus_listen_port']}
            label={intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.OBProxyConfig.PortExporter',
              defaultMessage: 'Exporter 端口',
            })}
          />

          {/* <Tooltip title="OBProxy 的 Exporter 端口，用于 Prometheus 拉取 OBProxy 监控数据。">
                  <QuestionCircleOutlined className="ml-10" />
                 </Tooltip> */}
        </Space>
      </Row>
      <ProForm.Item
        name={['obproxy', 'home_path']}
        style={{ width: '552px' }}
        rules={[
          {
            required: true,
            message: intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.OBProxyConfig.PleaseEnter',
              defaultMessage: '请输入',
            }),
          },
        ]}
        label={intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.OBProxyConfig.SoftwarePath',
          defaultMessage: '软件路径',
        })}
      >
        <Input addonAfter={<span>{obproxyAddonAfter}</span>} />
      </ProForm.Item>
      <div>
        <span
          onClick={() => handleCluserMoreChange()}
          className={styles.moreConfigText}
        >
          <span>
            {intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.OBProxyConfig.MoreConfigurations',
              defaultMessage: '更多配置',
            })}
          </span>
          {!isShowMoreConfig ? <RightOutlined /> : <DownOutlined />}
        </span>
      </div>
      <ConfigTable
        dataSource={proxyMoreConfig}
        customParameter={<Parameter />}
        showVisible={isShowMoreConfig}
        loading={proxyMoreLoading}
      />
    </ProCard>
  );
}
