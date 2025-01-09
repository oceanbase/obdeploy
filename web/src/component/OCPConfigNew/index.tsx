import { intl } from '@/utils/intl';
import { useRef } from 'react';
import { ProForm } from '@ant-design/pro-components';
import { Space, Button, message } from 'antd';
import { useModel } from 'umi';
import { useState } from 'react';

import ExitBtn from '../ExitBtn';
import CustomFooter from '../CustomFooter';
import ResourcePlan from './ResourcePlan';
import ServiceConfig from './ServiceConfig';
import UserConfig from './UserConfig';
import { getTailPath } from '@/utils/helper';

type TenantType = {
  name: {
    tenant_name: string;
  };
  password: string;
  resource: {
    cpu: number;
    memory: number;
  };
};

interface FormValues extends API.Components {
  auth?: {
    user?: string;
    password?: string;
    port: number;
  };
  ocpserver?: {
    home_path?: string;
    log_dir?: string;
    soft_dir?: string;
    ocp_site_url?: string;
    admin_password?: string;
    meta_tenant?: TenantType;
    monitor_tenant?: TenantType;
    memory_size?: number;
    port?: number;
    servers?: string[];
    manage_info?: {
      cluster: number;
      tenant: number;
      machine: number;
    };
  };
  launch_user?: string;
}

// 无site_url
const rulePath: any[] = [
  ['ocpserver', 'manage_info', 'cluster'],
  ['ocpserver', 'manage_info', 'tenant'],
  ['ocpserver', 'manage_info', 'machine'],
  ['ocpserver', 'memory_size'],
  ['ocpserver', 'meta_tenant', 'name', 'tenant_name'],
  ['ocpserver', 'meta_tenant', 'password'],
  ['ocpserver', 'meta_tenant', 'resource', 'cpu'],
  ['ocpserver', 'meta_tenant', 'resource', 'memory'],
  ['ocpserver', 'monitor_tenant', 'name', 'tenant_name'],
  ['ocpserver', 'monitor_tenant', 'password'],
  ['ocpserver', 'monitor_tenant', 'resource', 'cpu'],
  ['ocpserver', 'monitor_tenant', 'resource', 'memory'],
  ['ocpserver', 'admin_password'],
  ['ocpserver', 'home_path'],
  ['ocpserver', 'log_dir'],
  ['ocpserver', 'soft_dir'],
  ['ocpserver', 'port'],
];
export type MsgInfoType = {
  validateStatus: 'success' | 'error';
  errorMsg: string | null;
};

// 使用旧的数据库多 OCP部署选择
export default function OCPConfigNew({ setCurrent, current }: API.StepProp) {
  const isUseNewDBRef = useRef<boolean>(getTailPath() === 'install');
  const isOldDB = getTailPath() === 'configuration'
  const { ocpConfigData, setOcpConfigData, setErrorVisible, setErrorsList } =
    useModel('global');
  const { useRunningUser, isSingleOcpNode } = useModel('ocpInstallData');
  const { components = {}, auth = {}, launch_user } = ocpConfigData;
  const { ocpserver = {} } = components;
  const [form] = ProForm.useForm();
  const [adminMsgInfo, setAdminMsgInfo] = useState<MsgInfoType>();
  const [metaMsgInfo, setMetaMsgInfo] = useState<MsgInfoType>();
  const [tenantMsgInfo, setTenantMsgInfo] = useState<MsgInfoType>();
  const user = useRunningUser ? launch_user : auth.user;
  const prevStep = () => {
    const formValues = form.getFieldsValue(true);
    setData(formValues);
    setErrorVisible(false);
    setErrorsList([]);
    setCurrent(current - 1);
  };
  const setData = (dataSource: FormValues) => {
    let newOcpserver: any = {
      ...(ocpserver || {}),
      ...dataSource.ocpserver,
    };
    let result = {
      ...ocpConfigData,
      components: {
        ...components,
        ocpserver: newOcpserver,
      },
    };
    if (isOldDB) {
      if (dataSource.auth) result.auth = dataSource.auth;
      if (dataSource.launch_user) result.launch_user = dataSource.launch_user;
    }
    setOcpConfigData({ ...result });
  };

  const validateFields = async (rulePath?: any[]) => {
    if (
      adminMsgInfo?.validateStatus === 'error' ||
      metaMsgInfo?.validateStatus === 'error' ||
      tenantMsgInfo?.validateStatus === 'error'
    ) {
      //两种情况会是 error 不符合要求 或者 没有填写 没有填写form.validateFields是可以检测到的
      let errorPromises: Promise<any>[] = [];
      if (adminMsgInfo?.validateStatus === 'error') {
        errorPromises.push(
          Promise.reject({
            errorFields: [
              {
                errors: [adminMsgInfo.errorMsg],
                name: ['ocpserver', 'admin_password'],
              },
            ],
          }),
        );
      }
      if(metaMsgInfo?.validateStatus === 'error'){
        errorPromises.push(
          Promise.reject({
            errorFields: [
              {
                errors: [metaMsgInfo.errorMsg],
                name: ['ocpserver', 'meta_tenant', 'password'],
              },
            ],
          }),
        );
      }
      if(tenantMsgInfo?.validateStatus === 'error'){
        errorPromises.push(
          Promise.reject({
            errorFields: [
              {
                errors: [tenantMsgInfo.errorMsg],
                name: ['ocpserver', 'monitor_tenant', 'password'],
              },
            ],
          }),
        );
      }
      return Promise.allSettled([...errorPromises,form.validateFields(rulePath)])
    }
    return Promise.allSettled([form.validateFields(rulePath)]);
  };

  const sortErrorFields = (errorFields: any, sortArr: string[]) => {
    let res: any[] = [];
    for (let name of sortArr) {
      let target = errorFields?.find((errorField: any) => {
        if (errorField.name[0] === 'ocpserver') {
          return name === errorField.name[1];
        } else {
          return name === errorField.name[0];
        }
      });
      if (target) res.push(target);
    }
    return res;
  };

  const formValidScrollHelper = (result:PromiseSettledResult<any>[])=>{
    let errorFields = [];
    for(let item of result){
      if(item.status === 'rejected'){
        errorFields.push(...item.reason.errorFields)
      }
    }
    for (let errField of errorFields) {
      if (errField.name[1] && errField.name[1] === 'admin_password') {
        setAdminMsgInfo({
          validateStatus: 'error',
          errorMsg: errField.errors[0],
        });
      }
      if (
        errField.name[1] === 'meta_tenant' &&
        errField.name[2] === 'password'
      ) {
        setMetaMsgInfo({
          validateStatus: 'error',
          errorMsg: errField.errors[0],
        });
      }
      if (
        errField.name[1] === 'monitor_tenant' &&
        errField.name[2] === 'password'
      ) {
        setTenantMsgInfo({
          validateStatus: 'error',
          errorMsg: errField.errors[0],
        });
      }
    }
    const userBlock = ['auth', 'launch_user', 'servers'];
    const serviceBlock = [
      'admin_password',
      'soft_dir',
      'log_dir',
      'home_path',
      'ocp_site_url',
      'port',
    ];
    const resourceBlock = ['manage_info', 'memory_size'];
    const tenantBlock = ['meta_tenant', 'monitor_tenant'];
    let pathArr = isUseNewDBRef.current
      ? [...serviceBlock, ...resourceBlock, ...tenantBlock]
      : [...userBlock, ...serviceBlock, ...resourceBlock, ...tenantBlock];
    const sortFields = sortErrorFields(errorFields, pathArr);
    form.scrollToField(sortFields[0].name, {
      behavior: (actions) => {
        actions.forEach(({ el, top, left }) => {
          if (
            sortFields[0].name[0] === 'auth' ||
            sortFields[0].name[1] === 'servers' ||
            sortFields[0].name[0] === 'launch_user'
          ) {
            el.scrollTop = 0;
          } else if (serviceBlock.includes(sortFields[0].name[1])) {
            el.scrollTop = isUseNewDBRef.current ? 0 : 400;
          } else if (resourceBlock.includes(sortFields[0].name[1])) {
            el.scrollTop = isUseNewDBRef.current ? 400 : 900;
          } else if (tenantBlock.includes(sortFields[0].name[1])) {
            el.scrollTop = isUseNewDBRef.current ? 800 : 1300;
          }
          el.scrollLeft = left;
        });
      },
    });
    message.destroy();
  }

  const nextStep = async () => {
    let validatePromise: Promise<any>;
    if (
      isSingleOcpNode === false &&
      !form.getFieldsValue()?.ocpserver?.ocp_site_url
    ) {
      validatePromise = validateFields(rulePath);
    } else {
      validatePromise = validateFields();
    }
    validatePromise.then((result) => {
      if (result?.find((item: any) => item.status === 'rejected')) {
        formValidScrollHelper(result);
        return;
      }
      setData(result[0].value);
      setCurrent(current + 1);
      setErrorVisible(false);
      setErrorsList([]);
      window.scrollTo(0, 0);
    });
  };
  let home_path = undefined,
    log_dir = undefined,
    soft_dir = undefined;

  if (isUseNewDBRef.current) {
    let val = launch_user ? launch_user : auth.user;
    home_path = launch_user
      ? `/home/${launch_user}`
      : auth.user === 'root'
      ? '/root'
      : `/home/${auth.user}`;
    log_dir = `/home/${val}/logs`;
    soft_dir = `/home/${val}/software`;
  }

  let initialValues: FormValues = {
    ocpserver: {
      home_path: ocpserver?.home_path || home_path,
      log_dir: ocpserver?.log_dir || log_dir,
      soft_dir: ocpserver?.soft_dir || soft_dir,
      port: ocpserver?.port || 8080,
      ocp_site_url: ocpserver?.ocp_site_url || undefined,
      admin_password: ocpserver?.admin_password || undefined,
      memory_size: ocpserver?.memory_size || 4,
      meta_tenant: ocpserver?.meta_tenant || {
        resource: {
          cpu: 2,
          memory: 4,
        },
        name: {
          tenant_name: 'ocp_meta',
        },
      },
      monitor_tenant: ocpserver?.monitor_tenant || {
        resource: {
          cpu: 2,
          memory: 8,
        },
        name: {
          tenant_name: 'ocp_monitor',
        },
      },
      manage_info: ocpserver?.manage_info || {
        // cluster: 2,
        // tenant: 4,
        machine: 10,
      },
    },
    launch_user: launch_user || undefined,
  };

  if (!isUseNewDBRef.current) {
    initialValues = {
      ...initialValues,
      auth: {
        user: auth?.user || undefined,
        password: auth?.password || undefined,
        port: auth?.port || 22,
      },
      ocpserver: {
        ...initialValues.ocpserver,
        servers: ocpserver?.servers?.length ? ocpserver?.servers : undefined,
      },
      launch_user: launch_user || undefined,
    };
    rulePath.push(
      ...[
        ['auth', 'user'],
        ['auth', 'password'],
        'launch_user',
        ['ocpserver', 'servers'],
      ],
    );
  }

  return (
    <ProForm
      form={form}
      scrollToFirstError={true}
      initialValues={initialValues}
      submitter={false}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {!isUseNewDBRef.current && <UserConfig form={form} />}
        <ServiceConfig
          form={form}
          adminMsgInfo={adminMsgInfo}
          setAdminMsgInfo={setAdminMsgInfo}
        />
        <ResourcePlan
          form={form}
          metaMsgInfo={metaMsgInfo}
          tenantMsgInfo={tenantMsgInfo}
          setTenantMsgInfo={setTenantMsgInfo}
          setMetaMsgInfo={setMetaMsgInfo}
        />
        <CustomFooter>
          <ExitBtn />
          <Button
            data-aspm-click="ca54436.da43439"
            data-aspm-desc={intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.OcpConfigurationPreviousStep',
              defaultMessage: 'ocp配置-上一步',
            })}
            data-aspm-param={``}
            data-aspm-expo
            onClick={prevStep}
          >
            {intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.PreviousStep',
              defaultMessage: '上一步',
            })}
          </Button>
          <Button
            data-aspm-click="ca54436.da43440"
            data-aspm-desc={intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.OcpConfigurationNextStep',
              defaultMessage: 'ocp配置-下一步',
            })}
            data-aspm-param={``}
            data-aspm-expo
            type="primary"
            disabled={false}
            onClick={nextStep}
          >
            {intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.NextStep',
              defaultMessage: '下一步',
            })}
          </Button>
        </CustomFooter>
      </Space>
    </ProForm>
  );
}
