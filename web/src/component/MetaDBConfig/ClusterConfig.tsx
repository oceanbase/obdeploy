import { oceanbaseAddonAfter, PARAMETER_TYPE } from '@/constant/configuration';
import ConfigTable from '@/pages/Obdeploy/ClusterConfig/ConfigTable';
import { queryComponentParameters } from '@/services/ob-deploy-web/Components';
import {
  generateRandomPassword as generatePassword,
  getErrorInfo,
  passwordRules,
} from '@/utils';
import { formatMoreConfig } from '@/utils/helper';
import { intl } from '@/utils/intl';
import useRequest from '@/utils/useRequest';
import { DownOutlined, RightOutlined } from '@ant-design/icons';
import { ProFormText } from '@ant-design/pro-components';
import { useUpdateEffect } from 'ahooks';
import { Button, Row, Space } from 'antd';
import { FormInstance } from 'antd/lib/form';
import { useState } from 'react';
import { useModel } from 'umi';
import InputPort from '../InputPort';
import styles from './indexZh.less';

export default function ClusterConfig({ form }: { form: FormInstance<any> }) {
  const [clusterMoreLoading, setClusterMoreLoading] = useState(false);
  const { deployUser, useRunningUser } = useModel('ocpInstallData');
  const {
    ocpClusterMore,
    setOcpClusterMore,
    ocpConfigData,
    ocpClusterMoreConfig,
    setOcpClusterMoreConfig,
    setErrorVisible,
    setErrorsList,
    errorsList,
  } = useModel('global');
  const { components = {} } = ocpConfigData || {};
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
        const newClusterMoreConfig = formatMoreConfig(data?.items, false);
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

  useUpdateEffect(() => {
    const homePath =
      !useRunningUser && deployUser === 'root'
        ? `/${deployUser}`
        : `/home/${deployUser}`;
    form.setFieldValue(['oceanbase', 'home_path'], homePath);
  }, [deployUser]);

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
      />
    </div>
  );
}
