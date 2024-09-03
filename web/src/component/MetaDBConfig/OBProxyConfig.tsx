import { commonInputStyle, commonPortStyle } from '@/pages/constants';
import { intl } from '@/utils/intl';
import { ProCard, ProForm, ProFormSelect } from '@ant-design/pro-components';
import { useUpdateEffect } from 'ahooks';
import { Input, Row, Space, Switch } from 'antd';
import { FormInstance } from 'antd/lib/form';
import { useState } from 'react';
import { useModel } from 'umi';

import { obproxyAddonAfter, PARAMETER_TYPE } from '@/constant/configuration';
import ConfigTable from '@/pages/Obdeploy/ClusterConfig/ConfigTable';
import { queryComponentParameters } from '@/services/ob-deploy-web/Components';
import { getErrorInfo, ocpServersValidator } from '@/utils';
import { formatMoreConfig } from '@/utils/helper';
import useRequest from '@/utils/useRequest';
import InputPort from '../InputPort';
import styles from './index.less';
export default function OBProxyConfig({
  form,
  parameterRules,
}: {
  form: FormInstance<any>;
  parameterRules: any;
}) {
  const {
    ocpConfigData,
    proxyMoreConfig,
    setProxyMoreConfig,
    setErrorVisible,
    setErrorsList,
    errorsList,
  } = useModel('global');
  const { isShowMoreConfig, setIsShowMoreConfig, deployUser, useRunningUser } =
    useModel('ocpInstallData');
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

  useUpdateEffect(() => {
    const homePath =
      !useRunningUser && deployUser === 'root'
        ? `/${deployUser}`
        : `/home/${deployUser}`;
    form.setFieldValue(['obproxy', 'home_path'], homePath);
  }, [deployUser]);

  return (
    <ProCard
      title={intl.formatMessage({
        id: 'OBD.component.MetaDBConfig.OBProxyConfig.ObproxyConfiguration',
        defaultMessage: 'OBProxy 配置',
      })}
      bodyStyle={{ paddingBottom: 24 }}
      className={styles.proxyContainer}
    >
      <ProFormSelect
        mode="tags"
        name={['obproxy', 'servers']}
        fieldProps={{ style: commonInputStyle }}
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
        <Space size="large">
          <InputPort
            fieldProps={{ style: commonPortStyle }}
            name={['obproxy', 'listen_port']}
            label={intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.OBProxyConfig.SqlPort',
              defaultMessage: 'SQL 端口',
            })}
          />
          <InputPort
            fieldProps={{ style: commonPortStyle }}
            name={['obproxy', 'prometheus_listen_port']}
            label={intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.OBProxyConfig.PortExporter',
              defaultMessage: 'Exporter 端口',
            })}
          />
        </Space>
      </Row>
      <ProForm.Item
        name={['obproxy', 'home_path']}
        style={commonInputStyle}
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
      <div className={styles.moreSwitch}>
        {intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.OBProxyConfig.MoreConfigurations',
          defaultMessage: '更多配置',
        })}

        <Switch
          className="ml-20"
          checked={isShowMoreConfig}
          onChange={handleCluserMoreChange}
        />
      </div>
      <ConfigTable
        parameterRules={parameterRules}
        dataSource={proxyMoreConfig}
        showVisible={isShowMoreConfig}
        loading={proxyMoreLoading}
      />
    </ProCard>
  );
}
