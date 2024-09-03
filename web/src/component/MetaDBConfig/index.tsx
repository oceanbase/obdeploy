import { intl } from '@/utils/intl';
import type { EditableFormInstance } from '@ant-design/pro-components';
import { ProCard, ProForm } from '@ant-design/pro-components';
import { Button, Space } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { useModel } from 'umi';

import { PARAMETER_TYPE } from '@/constant/configuration';
import type { RulesDetail } from '@/pages/Obdeploy/ClusterConfig/ConfigTable';
import { parameterValidator } from '@/pages/Obdeploy/ClusterConfig/ConfigTable';
import { getPasswordRules } from '@/utils/helper';
import CustomFooter from '../CustomFooter';
import ExitBtn from '../ExitBtn';
import ClusterConfig from './ClusterConfig';
import DataBaseNodeConfig from './DataBaseNodeConfig';
import { formValidScorllHelper } from './helper';
import NodeConfig from './NodeConfig';
import OBProxyConfig from './OBProxyConfig';
import UserConfig from './UserConfig';

interface MetaDBConfig {
  setCurrent: React.Dispatch<React.SetStateAction<number>>;
  current: number;
}

interface FormValues extends API.Components {
  auth?: {
    user?: string;
    password?: string;
    port?: number;
  };
  ocpserver?: {
    servers?: string[];
  };
  launch_user?: string;
}

export const addonAfter = '/oceanbase';

export default function MetaDBConfig({ setCurrent, current }: MetaDBConfig) {
  const {
    ocpConfigData,
    setOcpConfigData,
    setErrorVisible,
    setErrorsList,
    ocpClusterMoreConfig,
    proxyMoreConfig,
  } = useModel('global');
  const { components = {}, auth, launch_user } = ocpConfigData;
  const { oceanbase = {}, ocpserver = {}, obproxy = {} } = components;
  const initDBConfigData = oceanbase?.topology?.length
    ? oceanbase?.topology?.map((item: API.Zone, index: number) => ({
        id: (Date.now() + index).toString(),
        ...item,
        servers: item?.servers?.map((server) => server?.ip),
      }))
    : [
        {
          id: (Date.now() + 1).toString(),
          name: 'zone1',
          servers: [],
          rootservice: undefined,
        },
        {
          id: (Date.now() + 2).toString(),
          name: 'zone2',
          servers: [],
          rootservice: undefined,
        },
        {
          id: (Date.now() + 3).toString(),
          name: 'zone3',
          servers: [],
          rootservice: undefined,
        },
      ];

  const [dbConfigData, setDBConfigData] =
    useState<API.DBConfig[]>(initDBConfigData);
  const finalValidate = useRef<boolean>(false);
  const tableFormRef = useRef<EditableFormInstance<API.DBConfig>>();
  const [parameterRules, setParameterRules] = useState<RulesDetail>({
    rules: [() => ({ validator: parameterValidator })],
    targetColumn: 'obproxy_sys_password',
  });
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
    let newAuth = { ...auth, ...dataSource.auth };
    let newComponents: API.Components = { ...components };
    dataSource.oceanbase.home_path;
    newComponents.obproxy = {
      ...(components.obproxy || {}),
      ...dataSource.obproxy,
      parameters: formatParameters(dataSource.obproxy?.parameters),
    };
    newComponents.ocpserver = {
      ...(components.ocpserver || {}),
      ...dataSource.ocpserver,
    };
    newComponents.oceanbase = {
      ...(components.oceanbase || {}),
      ...dataSource.oceanbase,
      topology: dbConfigData?.map((item) => ({
        ...item,
        servers: item?.servers?.map((server) => ({ ip: server })),
      })),
      parameters: formatParameters(dataSource.oceanbase?.parameters),
    };
    let newConfigData = {
      ...ocpConfigData,
      components: newComponents,
      auth: newAuth,
    };
    if (dataSource.launch_user) {
      newConfigData.launch_user = dataSource.launch_user;
    }
    setOcpConfigData(newConfigData);
  };
  const prevStep = () => {
    const formValues = form.getFieldsValue(true);
    setData(formValues);
    setErrorVisible(false);
    setErrorsList([]);
    setCurrent(current - 1);
  };

  const nextStep = () => {
    const tableFormRefValidate = () => {
      finalValidate.current = true;
      return tableFormRef?.current?.validateFields().then((values) => {
        return values;
      });
    };

    const formValidate = () => {
      return form.validateFields().then((values) => {
        return values;
      });
    };

    Promise.allSettled([formValidate(), tableFormRefValidate()]).then(
      (result) => {
        finalValidate.current = false;
        if (
          result[0].status === 'rejected' ||
          result[1].status === 'rejected'
        ) {
          formValidScorllHelper(result, form);
          return;
        }
        const formValues = result[0].value;
        setData(formValues);
        setCurrent(current + 1);
        setErrorVisible(false);
        setErrorsList([]);
        window.scrollTo(0, 0);
      },
    );
  };

  const [form] = ProForm.useForm();
  const passwordFormValue = ProForm.useWatch(
    ['obproxy', 'parameters', 'obproxy_sys_password', 'params'],
    form,
  );

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
      return [];
    }
  };
  const initialValues: FormValues = {
    auth: {
      user: auth?.user || undefined,
      password: auth?.password || undefined,
      port: auth?.port || 22,
    },
    ocpserver: {
      servers: ocpserver?.servers?.length ? ocpserver?.servers : undefined,
    },
    oceanbase: {
      root_password: oceanbase?.root_password || undefined,
      data_dir: oceanbase?.data_dir || '/data/1',
      redo_dir: oceanbase?.redo_dir || '/data/log1',
      mysql_port: oceanbase?.mysql_port || 2881,
      rpc_port: oceanbase?.rpc_port || 2882,
      home_path: oceanbase?.home_path || '/home/admin',
      parameters: getInitialParameters(
        oceanbase?.component,
        oceanbase?.parameters,
        ocpClusterMoreConfig,
      ),
    },
    obproxy: {
      servers: obproxy?.servers?.length ? obproxy?.servers : undefined,
      listen_port: obproxy?.listen_port || 2883,
      prometheus_listen_port: obproxy?.prometheus_listen_port || 2884,
      home_path: obproxy?.home_path || '/home',
      parameters: getInitialParameters(
        obproxy?.component,
        obproxy?.parameters,
        proxyMoreConfig,
      ),
    },
    launch_user: launch_user || undefined,
  };

  useEffect(() => {
    if (!passwordFormValue?.adaptive) {
      setParameterRules({
        rules: getPasswordRules('ob'),
        targetColumn: 'obproxy_sys_password',
      });
    } else {
      setParameterRules({
        rules: [() => ({ validator: parameterValidator })],
        targetColumn: 'obproxy_sys_password',
      });
    }
  }, [passwordFormValue]);

  return (
    <ProForm
      form={form}
      scrollToFirstError={true}
      submitter={false}
      validateTrigger={['onBlur', 'onChange']}
      grid={true}
      initialValues={initialValues}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <ProCard bodyStyle={{ paddingBottom: 24 }}>
          <UserConfig form={form} />
          <NodeConfig form={form} />
          <DataBaseNodeConfig
            tableFormRef={tableFormRef}
            dbConfigData={dbConfigData}
            finalValidate={finalValidate}
            setDBConfigData={setDBConfigData}
          />

          <ClusterConfig form={form} />
        </ProCard>
        <OBProxyConfig form={form} parameterRules={parameterRules} />
      </Space>
      <CustomFooter>
        <ExitBtn />
        <Button
          spm={intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.MetadbConfigurationPreviousStep',
            defaultMessage: 'MetaDB配置-上一步',
          })}
          onClick={prevStep}
        >
          {intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.PreviousStep',
            defaultMessage: '上一步',
          })}
        </Button>
        <Button
          spm={intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.MetadbConfigurationNext',
            defaultMessage: 'MetaDB配置-下一步',
          })}
          type="primary"
          disabled={false}
          onClick={nextStep}
        >
          {intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.NextStep',
            defaultMessage: '下一步',
          })}
        </Button>
      </CustomFooter>
    </ProForm>
  );
}
