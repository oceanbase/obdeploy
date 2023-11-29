import { intl } from '@/utils/intl';
import { Space, Input, Button, Row } from 'antd';
import { ProFormText, ProForm, ProFormDigit } from '@ant-design/pro-components';
import { RightOutlined, DownOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { FormInstance } from 'antd/lib/form';
import { useModel } from 'umi';

import {
  commonStyle,
  componentsConfig,
  componentVersionTypeToComponent,
} from '@/pages/constants';
import useRequest from '@/utils/useRequest';
import { queryComponentParameters } from '@/services/ob-deploy-web/Components';
import ConfigTable from '@/pages/Obdeploy/ClusterConfig/ConfigTable';
import { showConfigKeys } from '@/constant/configuration';
import Parameter from '@/pages/Obdeploy/ClusterConfig/Parameter';
import InputPort from '../InputPort';
import {
  generateRandomPassword as generatePassword,
  passwordRules,
  getErrorInfo,
} from '@/utils';
import styles from './indexZh.less';
import { oceanbaseAddonAfter } from '@/constant/configuration';

export default function ClusterConfig({ form }: { form: FormInstance<any> }) {
  const [isShowMoreConfig, setIsShowMoreConfig] = useState<boolean>(false);
  const [clusterMoreLoading, setClusterMoreLoading] = useState(false);
  const {
    ocpClusterMore,
    setOcpClusterMore,
    ocpConfigData,
    setOcpConfigData,
    ocpClusterMoreConfig,
    setOcpClusterMoreConfig,
    setErrorVisible,
    setErrorsList,
    errorsList,
  } = useModel('global');
  const { components = {}, home_path } = ocpConfigData || {};
  const { oceanbase = {} } = components;
  const [rootPassword, setRootPassword] = useState<string>(
    oceanbase.root_password || '',
  );
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
          if(parameterItem.name === "cluster_id")parameterItem.default = '0'
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
        setOcpClusterMoreConfig(newClusterMoreConfig);
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
      setOcpClusterMore(false);
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    }
    setClusterMoreLoading(false);
  };

  const handleCluserMoreChange = () => {
    setOcpClusterMore(!ocpClusterMore);
    if (!ocpClusterMoreConfig?.length) {
      getClusterMoreParamsters();
    }
  };

  const setPassword = (password: string) => {
    form.setFieldValue(['oceanbase', 'root_password'], password);
    form.validateFields([['oceanbase', 'root_password']]);
    setRootPassword(password);
  };

  const generateRandomPassword = () => {
    const password = generatePassword();
    setPassword(password);
  };

  useEffect(() => {
    if (isShowMoreConfig) {
    }
  }, [isShowMoreConfig]);

  return (
    <div className={styles.clusterContainer}>
      <p className={styles.titleText}>
        {intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.ClusterConfig.ClusterConfiguration',
          defaultMessage: '集群配置',
        })}
      </p>
      <div className={styles.passwordInput}>
        <ProFormText.Password
          name={['oceanbase', 'root_password']}
          label={intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.ClusterConfig.RootSysPassword',
            defaultMessage: 'root@sys 密码',
          })}
          rules={passwordRules}
          fieldProps={{
            style: { width: 328 },
            autoComplete: 'new-password',
            value: rootPassword,
            onChange: (e) => {
              setPassword(e.target.value);
            },
          }}
          placeholder={intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.ClusterConfig.PleaseEnter',
            defaultMessage: '请输入',
          })}
          validateFirst
        />

        <Button
          onClick={generateRandomPassword}
          style={{ borderRadius: '6px', margin: '0 0 24px 8px' }}
        >
          {intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.ClusterConfig.RandomlyGenerated',
            defaultMessage: '随机生成',
          })}
        </Button>
      </div>

      <ProFormText
        name={['oceanbase', 'home_path']}
        label={intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.ClusterConfig.SoftwareInstallationPath',
          defaultMessage: '软件安装路径',
        })}
        rules={[
          {
            required: true,
            message: intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.ClusterConfig.PleaseEnter',
              defaultMessage: '请输入',
            }),
          },
        ]}
        fieldProps={{
          addonAfter: <span>{oceanbaseAddonAfter}</span>,
          style: { width: 552 },
        }}
      />

      <ProFormText
        name={['oceanbase', 'data_dir']}
        label={intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.ClusterConfig.DataPath',
          defaultMessage: '数据路径',
        })}
        rules={[
          {
            required: true,
            message: intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.ClusterConfig.PleaseEnter',
              defaultMessage: '请输入',
            }),
          },
        ]}
        fieldProps={{ style: { width: 552 } }}
      />

      <ProFormText
        name={['oceanbase', 'redo_dir']}
        label={intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.ClusterConfig.LogPath',
          defaultMessage: '日志路径',
        })}
        rules={[
          {
            required: true,
            message: intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.ClusterConfig.PleaseEnter',
              defaultMessage: '请输入',
            }),
          },
        ]}
        fieldProps={{ style: { width: 552 } }}
      />

      <Row className={styles.portContainer}>
        <Space size="middle">
          <InputPort
            name={['oceanbase', 'mysql_port']}
            label={intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.ClusterConfig.SqlPort.1',
              defaultMessage: 'SQL 端口',
            })}
          />
          <InputPort
            name={['oceanbase', 'rpc_port']}
            label={intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.ClusterConfig.RpcPort.1',
              defaultMessage: 'RPC 端口',
            })}
          />
        </Space>
      </Row>
      <div>
        <span
          onClick={() => handleCluserMoreChange()}
          className={styles.moreConfigText}
        >
          <span>
            {intl.formatMessage({
              id: 'OBD.component.MetaDBConfig.ClusterConfig.MoreConfigurations',
              defaultMessage: '更多配置',
            })}
          </span>
          {!ocpClusterMore ? <RightOutlined /> : <DownOutlined />}
        </span>
      </div>
      <ConfigTable
        showVisible={ocpClusterMore}
        dataSource={ocpClusterMoreConfig}
        loading={clusterMoreLoading}
        customParameter={<Parameter />}
      />
    </div>
  );
}
