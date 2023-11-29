import { intl } from '@/utils/intl';
import { ProCard, ProFormText, ProFormDigit } from '@ant-design/pro-components';
import { FormInstance } from 'antd/lib/form';
import { Alert, Row, Col, message } from 'antd';
import { useState } from 'react';
import { useModel } from 'umi';

import { generateRandomPassword as generatePassword } from '@/utils';
import { copyText } from '@/utils/helper';
import CustomPasswordInput from '../CustomPasswordInput';
import { resourceMap } from '@/pages/constants';
import styles from './index.less';
import { MsgInfoType } from './index';
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
    >
      <Alert
        type="info"
        showIcon={true}
        description={intl.formatMessage({
          id: 'OBD.component.OCPConfigNew.ResourcePlan.TheOcpServiceRunsWith',
          defaultMessage:
            'OCP 服务在运行过程中会有计算和存储资源开销，您需要根据待管理的对象规模进行资源规划，包括 OCP 服务、MetaDB 和 MonitorDB。',
        })}
        style={{
          marginBottom: 24,
          // height: 54
        }}
      />

      <p>
        {intl.formatMessage({
          id: 'OBD.component.OCPConfigNew.ResourcePlan.YouAreExpectedToNeed',
          defaultMessage: '您预计需要管理：',
        })}
      </p>
      <Row style={{ alignItems: 'center' }}>
        <ProFormDigit
          name={['ocpserver', 'manage_info', 'machine']}
          label={intl.formatMessage({
            id: 'OBD.component.OCPConfigNew.ResourcePlan.Host',
            defaultMessage: '主机',
          })}
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
            style: { width: 145, marginRight: 8 },
            onChange: (inputHosts) => handleChangeHosts(inputHosts),
          }}
        />

        <span style={{ lineHeight: '32px' }}>
          {intl.formatMessage({
            id: 'OBD.component.OCPConfigNew.ResourcePlan.Table',
            defaultMessage: '台',
          })}
        </span>
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
          fieldProps={{ style: { width: 127 } }}
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
          label={intl.formatMessage({
            id: 'OBD.component.OCPConfigNew.ResourcePlan.OcpApplicationMemory',
            defaultMessage: 'OCP 应用内存',
          })}
        />
        <span style={{ marginLeft: '12px' }}>GiB</span>
      </Row>
      {/* <ProForm.Item name={['ocpserver', 'memory_size']} label="内存">
          <InputNumber />
          <span style={{ marginLeft: '12px' }}>GIB</span>
         </ProForm.Item> */}
      <p className={styles.titleText}>
        {intl.formatMessage({
          id: 'OBD.component.OCPConfigNew.ResourcePlan.MetadataTenantConfiguration',
          defaultMessage: '元信息租户配置',
        })}
      </p>
      <Row>
        <Col style={{ marginRight: 12 }}>
          <ProFormText
            name={['ocpserver', 'meta_tenant', 'name', 'tenant_name']}
            label={intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ResourcePlan.TenantName',
              defaultMessage: '租户名称',
            })}
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
        </Col>
        <Col>
          <CustomPasswordInput
            msgInfo={metaMsgInfo}
            setMsgInfo={setMetaMsgInfo}
            form={form}
            onChange={handleSetTenantPassword}
            value={tenantPassword}
            name={['ocpserver', 'meta_tenant', 'password']}
            label={intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ResourcePlan.Password',
              defaultMessage: '密码',
            })}
          />
        </Col>
      </Row>
      <Row>
        <ProFormDigit
          name={['ocpserver', 'meta_tenant', 'resource', 'cpu']}
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ResourcePlan.PleaseEnter',
                defaultMessage: '请输入',
              }),
            },
          ]}
          label="CPU"
        />

        <span style={{ margin: '0 12px 0 14px', lineHeight: '86px' }}>
          VCPUS
        </span>
        <ProFormDigit
          name={['ocpserver', 'meta_tenant', 'resource', 'memory']}
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.component.OCPConfigNew.ResourcePlan.PleaseEnter',
                defaultMessage: '请输入',
              }),
            },
          ]}
          label={intl.formatMessage({
            id: 'OBD.component.OCPConfigNew.ResourcePlan.Memory',
            defaultMessage: '内存',
          })}
        />

        <span style={{ lineHeight: '86px', marginLeft: '12px' }}>GiB</span>
      </Row>
      <p className={styles.titleText}>
        {intl.formatMessage({
          id: 'OBD.component.OCPConfigNew.ResourcePlan.MonitorDataTenantConfiguration',
          defaultMessage: '监控数据租户配置',
        })}
      </p>
      <Row>
        <Col style={{ marginRight: 12 }}>
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
            label={intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ResourcePlan.TenantName',
              defaultMessage: '租户名称',
            })}
          />
        </Col>
        <Col>
          <CustomPasswordInput
            msgInfo={tenantMsgInfo}
            setMsgInfo={setTenantMsgInfo}
            form={form}
            onChange={handleSetMonitorPassword}
            value={monitorPassword}
            name={['ocpserver', 'monitor_tenant', 'password']}
            label={intl.formatMessage({
              id: 'OBD.component.OCPConfigNew.ResourcePlan.Password',
              defaultMessage: '密码',
            })}
          />
        </Col>
      </Row>
      <Row>
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
          label="CPU"
        />

        <span style={{ margin: '0 12px 0 14px', lineHeight: '86px' }}>
          VCPUS
        </span>
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
          label={intl.formatMessage({
            id: 'OBD.component.OCPConfigNew.ResourcePlan.Memory',
            defaultMessage: '内存',
          })}
        />

        <span style={{ lineHeight: '86px', marginLeft: '12px' }}>GiB</span>
      </Row>
    </ProCard>
  );
}
