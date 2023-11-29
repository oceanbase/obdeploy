import { intl } from '@/utils/intl';
import { Row, Col, Form, Modal, Card, Spin } from '@oceanbase/design';
import React, { useEffect, useState } from 'react';
// import { Pie } from '@alipay/ob-charts';
import { useRequest } from 'ahooks';
import { Alert } from 'antd';
import { errorHandler } from '@/utils';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import SliderAndInputNumber from '@/component/SliderAndInputNumber';
import { find } from 'lodash';

export interface ModifyResourcePoolModalProps {
  currentOcpDeploymentConfig?: any;
  createOCPDeployment: (params) => void;
  monitorDisplay?: boolean;
  visible?: boolean;
  loading?: boolean;
  id: number;
}

const ModifyResourcePoolModal: React.FC<ModifyResourcePoolModalProps> = ({
  currentOcpDeploymentConfig,
  createOCPDeployment,
  monitorDisplay,
  loading,
  visible,
  id,
  ...restProps
}) => {
  const [form] = Form.useForm();
  const { validateFields, setFieldsValue } = form;

  // OCP-SERVER
  const [ocpCpuFree, setOcpCpuFree] = useState(1);
  const [ocpMemoryFree, setOcpMemoryFree] = useState(1);

  // 剩余cpu
  const [cpu_Free, setCpu_Free] = useState(10);
  // // 剩余内存
  const [memory_Free, setMemory_Free] = useState(10);

  // 其他已使用内存
  const [otherUsedMemory, setOtherUsedMemory] = useState(1);

  // 剩余cpu
  const [cpuFree, setCpuFree] = useState(1);
  // 剩余内存
  const [memoryFree, setMemoryFree] = useState(1);

  // OCP 租户
  const [ocpTenantCpuFree, setOcpTenantCpuFree] = useState(2);
  const [ocpTenantMemoryFree, setOcpTenantMemoryFree] = useState(4);

  // 原信息租户
  const [tenantCpuFree, setTenantCpuFree] = useState(2);
  const [tenantMemoryFree, setTenantMemoryFree] = useState(4);

  // 监控数据租户
  const [monitorCpuFree, setMonitorCpuFree] = useState(4);
  const [monitorMemory, setMonitorMemory] = useState(8);

  // 查询主机的资源
  const {
    data: resourceData,
    run: getOcpDeploymentResource,
    loading: getOcpDeploymentResourceLoading,
  } = useRequest(OCP.getOcpDeploymentResource, {
    manual: true,
    onSuccess: (res) => {
      if (res.success) {
        const ocpDeploymentResource = res?.data || {};
        const { cpu_free, memory_free, memory_total } =
          ocpDeploymentResource?.metadb?.servers?.length > 0
            ? ocpDeploymentResource?.metadb?.servers[0]
            : {};

        setCpu_Free(cpu_free);
        setMemory_Free(memory_free);
        setOcpCpuFree(cpu_free);
        setOcpMemoryFree(memory_free > 5 ? 5 : 1);
        setOtherUsedMemory(memory_total - memory_free);
        setCpuFree(cpu_free > 7 ? cpu_free - 7 : cpu_free);
        setMemoryFree(memory_free - (memory_free > 5 ? 13 : 14));
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });
  const ocpResource = resourceData?.data;

  useEffect(() => {
    // 如果用户如有上次的手动输入，需要采用用户输入
    if (currentOcpDeploymentConfig?.id) {
      const { meta_tenant, monitor_tenant, parameters } =
        currentOcpDeploymentConfig?.config;
      setFieldsValue({
        ocpMemory:
          find(parameters, (item) => item?.name === 'memory_size')?.value || 1,
        ocpCPU: find(parameters, (item) => item?.name === 'ocpCPU')?.value || 1,
        tenantCPU: meta_tenant?.resource?.cpu || 2,
        tenantMemory: meta_tenant?.resource?.memory || 3,
        monitorCPU: monitor_tenant?.resource?.cpu || 4,
        monitorMemory: monitor_tenant?.resource?.memory || 8,
      });
    }
  }, [currentOcpDeploymentConfig?.id]);

  useEffect(() => {
    if (id && visible) {
      getOcpDeploymentResource({ id });
    }
  }, [id, visible]);

  const handleSubmit = () => {
    validateFields().then((values) => {
      if (createOCPDeployment) {
        createOCPDeployment(values);
      }
    });
  };

  const resourceList = [
    {
      type: intl.formatMessage({
        id: 'OBD.component.ModifyOCPResourcePoolModal.OcpServerMemory',
        defaultMessage: 'OCP-Server 内存',
      }),
      value: ocpMemoryFree,
    },
    ...(!monitorDisplay
      ? [
          {
            type: intl.formatMessage({
              id: 'OBD.component.ModifyOCPResourcePoolModal.OcpTenantMemory',
              defaultMessage: 'OCP 租户内存',
            }),
            value: ocpTenantMemoryFree,
          },
        ]
      : [
          {
            type: intl.formatMessage({
              id: 'OBD.component.ModifyOCPResourcePoolModal.MetadataTenantMemory',
              defaultMessage: '元信息租户 内存',
            }),
            value: tenantMemoryFree,
          },
          {
            type: intl.formatMessage({
              id: 'OBD.component.ModifyOCPResourcePoolModal.MonitorDataTenantMemory',
              defaultMessage: '监控数据租户内存',
            }),
            value: monitorMemory,
          },
        ]),

    {
      type: intl.formatMessage({
        id: 'OBD.component.ModifyOCPResourcePoolModal.OtherUsedMemory',
        defaultMessage: '其他已使用内存',
      }),
      value: otherUsedMemory,
    },
    {
      type: intl.formatMessage({
        id: 'OBD.component.ModifyOCPResourcePoolModal.RemainingMemory',
        defaultMessage: '剩余内存',
      }),
      value: memoryFree,
    },
  ];

  const config1 = {
    data: resourceList,
    angleField: 'value',
    colorField: 'type',
    innerRadius: 0.8,
    isDonut: true,
    lineWidth: 20,
    label: false,
    style: {
      textAlign: 'center',
      fontSize: 14,
    },
  };

  return (
    <Modal
      width="666px"
      title={intl.formatMessage({
        id: 'OBD.component.ModifyOCPResourcePoolModal.ResourceAllocation',
        defaultMessage: '资源分配',
      })}
      destroyOnClose={true}
      visible={visible}
      onOk={handleSubmit}
      confirmLoading={loading}
      {...restProps}
    >
      <Spin spinning={getOcpDeploymentResourceLoading || !ocpResource}>
        <Alert
          type="info"
          showIcon={true}
          message={intl.formatMessage({
            id: 'OBD.component.ModifyOCPResourcePoolModal.AccordingToTheResourcesOf',
            defaultMessage:
              '根据当前主机环境的资源情况，为 OCP 相关服务分配资源如下',
          })}
          style={{
            margin: '16px 0',
            height: 54,
          }}
        />

        <Form
          form={form}
          preserve={false}
          layout="inline"
          hideRequiredMark={true}
          className="form-with-small-margin"
        >
          <Row gutter={[8, 12]}>
            <Col span={24}>
              <Card
                bordered={false}
                divided={false}
                title={intl.formatMessage({
                  id: 'OBD.component.ModifyOCPResourcePoolModal.MemoryAllocationMapGib',
                  defaultMessage: '内存分配图（GiB）',
                })}
                className="card-background-color"
              >
                {/* <Pie height={120} {...config1} /> */}
              </Card>
            </Col>
            <Col span={24}>
              <Card
                bordered={false}
                divided={false}
                title="OCP-Server"
                className="card-background-color"
              >
                <Form.Item
                  style={{ width: '100%' }}
                  label="CPU"
                  name="ocpCPU"
                  initialValue={1}
                >
                  <SliderAndInputNumber
                    min={1}
                    max={cpu_Free}
                    addonAfter="vCPUs"
                    onChange={(val) => {
                      setOcpCpuFree(val);
                      setCpuFree(
                        cpu_Free -
                          val -
                          (monitorDisplay
                            ? ocpTenantCpuFree
                            : tenantCpuFree + monitorCpuFree),
                      );
                    }}
                  />
                </Form.Item>
                <Form.Item
                  style={{ width: '100%' }}
                  label={intl.formatMessage({
                    id: 'OBD.component.ModifyOCPResourcePoolModal.Memory',
                    defaultMessage: '内存',
                  })}
                  name="ocpMemory"
                  initialValue={1}
                >
                  <SliderAndInputNumber
                    min={1}
                    max={memory_Free}
                    onChange={(val) => {
                      setOcpMemoryFree(val);
                      setMemoryFree(
                        memory_Free -
                          val -
                          (monitorDisplay
                            ? ocpTenantMemoryFree
                            : tenantMemoryFree + monitorMemory),
                      );
                    }}
                  />
                </Form.Item>
              </Card>
            </Col>
            {/* 当 ./ocp_installer.sh launch 以 -mix 参数启动时，仅展示 OCP 租户，不再区分元信息/监控数据租户，仅通过数据库用户名做访问区分，如图 */}
            {!monitorDisplay ? (
              <Col span={24}>
                <Card
                  bordered={false}
                  divided={false}
                  title={intl.formatMessage({
                    id: 'OBD.component.ModifyOCPResourcePoolModal.OcpTenant',
                    defaultMessage: 'OCP 租户',
                  })}
                  className="card-background-color"
                >
                  <Form.Item label="CPU" name="ocpTenantCPU" initialValue={3}>
                    <SliderAndInputNumber
                      min={1}
                      max={cpu_Free}
                      addonAfter="vCPUs"
                      onChange={(val) => {
                        setOcpTenantCpuFree(val);
                        setCpuFree(cpu_Free - val - ocpCpuFree);
                      }}
                    />
                  </Form.Item>
                  <Form.Item
                    label={intl.formatMessage({
                      id: 'OBD.component.ModifyOCPResourcePoolModal.Memory',
                      defaultMessage: '内存',
                    })}
                    name="ocpTenantMemory"
                    initialValue={5}
                  >
                    <SliderAndInputNumber
                      min={5}
                      max={memory_Free}
                      onChange={(val) => {
                        setOcpTenantMemoryFree(val);
                        setMemoryFree(memory_Free - val - ocpMemoryFree);
                      }}
                    />
                  </Form.Item>
                </Card>
              </Col>
            ) : (
              <>
                <Col span={24}>
                  <Card
                    bordered={false}
                    divided={false}
                    title={intl.formatMessage({
                      id: 'OBD.component.ModifyOCPResourcePoolModal.MetadataTenant',
                      defaultMessage: '元信息租户',
                    })}
                    className="card-background-color"
                  >
                    <Form.Item label="CPU" name="tenantCPU" initialValue={2}>
                      <SliderAndInputNumber
                        min={1}
                        max={cpu_Free}
                        addonAfter="vCPUs"
                        onChange={(val) => {
                          setTenantCpuFree(val);
                          setCpuFree(
                            cpu_Free - val - (ocpCpuFree + monitorCpuFree),
                          );
                        }}
                      />
                    </Form.Item>
                    <Form.Item
                      label={intl.formatMessage({
                        id: 'OBD.component.ModifyOCPResourcePoolModal.Memory',
                        defaultMessage: '内存',
                      })}
                      name="tenantMemory"
                      initialValue={3}
                    >
                      <SliderAndInputNumber
                        min={2}
                        max={memory_Free}
                        onChange={(val) => {
                          setTenantMemoryFree(val);
                          setMemoryFree(
                            memory_Free - val - (ocpMemoryFree + monitorMemory),
                          );
                        }}
                      />
                    </Form.Item>
                  </Card>
                </Col>
                <Col span={24}>
                  <Card
                    bordered={false}
                    divided={false}
                    title={intl.formatMessage({
                      id: 'OBD.component.ModifyOCPResourcePoolModal.MonitorDataTenants',
                      defaultMessage: '监控数据租户',
                    })}
                    className="card-background-color"
                  >
                    <Form.Item label="CPU" name="monitorCPU" initialValue={4}>
                      <SliderAndInputNumber
                        min={2}
                        max={cpu_Free}
                        addonAfter="vCPUs"
                        onChange={(val) => {
                          setMonitorCpuFree(val);
                          setCpuFree(
                            cpu_Free - val - (ocpCpuFree + tenantCpuFree),
                          );
                        }}
                      />
                    </Form.Item>
                    <Form.Item
                      label={intl.formatMessage({
                        id: 'OBD.component.ModifyOCPResourcePoolModal.Memory',
                        defaultMessage: '内存',
                      })}
                      name="monitorMemory"
                      initialValue={8}
                    >
                      <SliderAndInputNumber
                        min={4}
                        max={memory_Free}
                        onChange={(val) => {
                          setMonitorMemory(val);
                          setMemoryFree(
                            memory_Free -
                              val -
                              (ocpMemoryFree + tenantMemoryFree),
                          );
                        }}
                      />
                    </Form.Item>
                  </Card>
                </Col>
              </>
            )}
          </Row>
        </Form>
      </Spin>
    </Modal>
  );
};

export default ModifyResourcePoolModal;
