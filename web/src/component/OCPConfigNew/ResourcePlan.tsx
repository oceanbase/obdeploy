import { commonInputStyle, commonPortStyle } from '@/pages/constants';
import { intl } from '@/utils/intl';
import { ProCard, ProFormDigit, ProFormText } from '@ant-design/pro-components';
import { Row, Space } from 'antd';
import { FormInstance } from 'antd/lib/form';
import { useState } from 'react';
import { useModel } from 'umi';
import CustomAlert from '../CustomAlert';

import { resourceMap } from '@/pages/constants';
import CustomPasswordInput from '../CustomPasswordInput';
import { MsgInfoType } from './index';
import styles from './index.less';
interface ResourcePlanProps {
  form: FormInstance<any>;
  metaMsgInfo: MsgInfoType;
  tenantMsgInfo: MsgInfoType;
  setTenantMsgInfo: React.Dispatch<
    React.SetStateAction<MsgInfoType | undefined>
  >;

  setMetaMsgInfo: React.Dispatch<React.SetStateAction<MsgInfoType | undefined>>;
}

type ResourceType = {
  hosts: number;
  cpu: number;
  memory: number;
};

const lableStyle = { color: '#132039' };

export default function ResourcePlan({
  form,
  metaMsgInfo,
  tenantMsgInfo,
  setTenantMsgInfo,
  setMetaMsgInfo,
}: ResourcePlanProps) {
  const { ocpConfigData = {} } = useModel('global');
  const { components = {} } = ocpConfigData;
  const { ocpserver = {} } = components;
  const { meta_tenant = {}, monitor_tenant = {} } = ocpserver;
  const [tenantPassword, setTenantPassword] = useState<string>(
    meta_tenant.password || '',
  );
  const [monitorPassword, setMonitorPassword] = useState<string>(
    monitor_tenant.password || '',
  );

  const handleSetTenantPassword = (password: string) => {
    form.setFieldValue(['ocpserver', 'meta_tenant', 'password'], password);
    form.validateFields([['ocpserver', 'meta_tenant', 'password']]);
    setTenantPassword(password);
  };

  const handleSetMonitorPassword = (password: string) => {
    form.setFieldValue(['ocpserver', 'monitor_tenant', 'password'], password);
    form.validateFields([['ocpserver', 'monitor_tenant', 'password']]);
    setMonitorPassword(password);
  };

  const hostsMapValue = (inputHosts: number, resourceMap: ResourceType[]) => {
    let cpuRes, memoryRes;
    const { cpu: maxCpu, memory: maxMemory } =
      resourceMap[resourceMap.length - 1];
    for (let item of resourceMap) {
      if (inputHosts <= item.hosts) {
        cpuRes = item.cpu;
        memoryRes = item.memory;
        break;
      }
    }
    if (!cpuRes) cpuRes = maxCpu;
    if (!memoryRes) memoryRes = maxMemory;
    return [cpuRes, memoryRes];
  };

  const handleChangeHosts = (inputHosts: number) => {
    const metaDBMap = resourceMap['metaDB'],
      monitorDBMap = resourceMap['monitorDB'],
      OCPMap = resourceMap['OCP'];
    const [metaDBCpu, metaDBMemory] = hostsMapValue(inputHosts, metaDBMap);
    const [monitorDBCpu, monitorDBMemory] = hostsMapValue(
      inputHosts,
      monitorDBMap,
    );
    const [_, ocpMemory] = hostsMapValue(inputHosts, OCPMap);
    form.setFieldsValue({
      ocpserver: {
        memory_size: ocpMemory,
        monitor_tenant: {
          resource: {
            cpu: monitorDBCpu,
            memory: monitorDBMemory,
          },
        },
        meta_tenant: {
          resource: {
            cpu: metaDBCpu,
            memory: metaDBMemory,
          },
        },
      },
    });
  };

  return (
    <ProCard
      title={intl.formatMessage({
        id: 'OBD.component.OCPConfigNew.ResourcePlan.ResourcePlanning',
        defaultMessage: '资源规划',
      })}
      bodyStyle={{ paddingBottom: 0 }}
    >
      <CustomAlert
        type="info"
        showIcon={true}
        message={intl.formatMessage({
          id: 'OBD.component.OCPConfigNew.ResourcePlan.TheOcpServiceRunsWith',
          defaultMessage:
            'OCP 服务在运行过程中会有计算和存储资源开销，您需要根据待管理的对象规模进行资源规划，包括 OCP 服务、MetaDB 和 MonitorDB。',
        })}
        style={{ height: 40 }}
      />

      <Row style={{ alignItems: 'center', marginTop: 16 }}>
        <ProFormDigit
          name={['ocpserver', 'manage_info', 'machine']}
          label={
            <span style={lableStyle}>
              {intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ResourcePlan.EstimatedNumberOfManagementHosts',
                defaultMessage: '预计管理主机数量（台）',
              })}
            </span>
          }
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ResourcePlan.PleaseEnter',
                defaultMessage: '请输入',
              }),
            },
          ]}
          fieldProps={{
            addonBefore: intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ResourcePlan.Less',
              defaultMessage: '小于',
            }),
            style: commonPortStyle,
            onChange: (inputHosts) => handleChangeHosts(inputHosts),
          }}
        />
      </Row>
      <p className={styles.titleText}>
        {intl.formatMessage({
          id: 'OBD.component.OCPConfigNew.ResourcePlan.ResourceConfiguration',
          defaultMessage: '资源配置',
        })}
      </p>
      <Row style={{ alignItems: 'center' }}>
        {' '}
        <ProFormDigit
          fieldProps={{ style: commonPortStyle }}
          name={['ocpserver', 'memory_size']}
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ResourcePlan.PleaseEnter',
                defaultMessage: '请输入',
              }),
            },
          ]}
          label={
            <span style={lableStyle}>
              {intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ResourcePlan.OcpApplicationMemoryGib',
                defaultMessage: 'OCP 应用内存（GiB）',
              })}
            </span>
          }
        />
      </Row>
      <p className={styles.titleText}>
        {intl.formatMessage({
          id: 'OBD.component.OCPConfigNew.ResourcePlan.MetadataTenantConfiguration',
          defaultMessage: '元信息租户配置',
        })}
      </p>
      <ProFormText
        name={['ocpserver', 'meta_tenant', 'name', 'tenant_name']}
        label={
          <span style={lableStyle}>
            {intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ResourcePlan.TenantName',
              defaultMessage: '租户名称',
            })}
          </span>
        }
        fieldProps={{ style: commonInputStyle }}
        rules={[
          {
            required: true,
            message: intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ResourcePlan.EnterATenantName',
              defaultMessage: '请输入租户名称',
            }),
          },
        ]}
      />

      <CustomPasswordInput
        msgInfo={metaMsgInfo}
        setMsgInfo={setMetaMsgInfo}
        form={form}
        onChange={handleSetTenantPassword}
        value={tenantPassword}
        useFor="ob"
        name={['ocpserver', 'meta_tenant', 'password']}
        style={commonInputStyle}
        innerInputStyle={{ width: 388 }}
        label={
          <span style={lableStyle}>
            {intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ResourcePlan.Password',
              defaultMessage: '密码',
            })}
          </span>
        }
      />

      <Space size={'large'}>
        <ProFormDigit
          name={['ocpserver', 'meta_tenant', 'resource', 'cpu']}
          fieldProps={{ style: commonPortStyle }}
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ResourcePlan.PleaseEnter',
                defaultMessage: '请输入',
              }),
            },
          ]}
          label={<span style={lableStyle}>CPU（VCPUS）</span>}
        />

        <ProFormDigit
          name={['ocpserver', 'meta_tenant', 'resource', 'memory']}
          fieldProps={{ style: commonPortStyle }}
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ResourcePlan.PleaseEnter',
                defaultMessage: '请输入',
              }),
            },
          ]}
          label={
            <span style={lableStyle}>
              {intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ResourcePlan.MemoryGib',
                defaultMessage: '内存（GiB）',
              })}
            </span>
          }
        />
      </Space>
      <p className={styles.titleText}>
        {intl.formatMessage({
          id: 'OBD.component.OCPConfigNew.ResourcePlan.MonitorDataTenantConfiguration',
          defaultMessage: '监控数据租户配置',
        })}
      </p>
      <ProFormText
        name={['ocpserver', 'monitor_tenant', 'name', 'tenant_name']}
        rules={[
          {
            required: true,
            message: intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ResourcePlan.PleaseEnter',
              defaultMessage: '请输入',
            }),
          },
        ]}
        fieldProps={{ style: commonInputStyle }}
        label={
          <span style={lableStyle}>
            {intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ResourcePlan.TenantName',
              defaultMessage: '租户名称',
            })}
          </span>
        }
      />

      <CustomPasswordInput
        msgInfo={tenantMsgInfo}
        setMsgInfo={setTenantMsgInfo}
        form={form}
        onChange={handleSetMonitorPassword}
        value={monitorPassword}
        useFor="ob"
        name={['ocpserver', 'monitor_tenant', 'password']}
        style={commonInputStyle}
        innerInputStyle={{ width: 388 }}
        label={
          <span style={lableStyle}>
            {intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ResourcePlan.Password',
              defaultMessage: '密码',
            })}
          </span>
        }
      />

      <Space size="large">
        <ProFormDigit
          name={['ocpserver', 'monitor_tenant', 'resource', 'cpu']}
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ResourcePlan.PleaseEnter',
                defaultMessage: '请输入',
              }),
            },
          ]}
          fieldProps={{ style: commonPortStyle }}
          label={<span style={lableStyle}>CPU（VCPUS）</span>}
        />

        <ProFormDigit
          name={['ocpserver', 'monitor_tenant', 'resource', 'memory']}
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ResourcePlan.PleaseEnter',
                defaultMessage: '请输入',
              }),
            },
          ]}
          fieldProps={{ style: commonPortStyle }}
          label={
            <span style={lableStyle}>
              {intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ResourcePlan.MemoryGib',
                defaultMessage: '内存（GiB）',
              })}
            </span>
          }
        />
      </Space>
    </ProCard>
  );
}
