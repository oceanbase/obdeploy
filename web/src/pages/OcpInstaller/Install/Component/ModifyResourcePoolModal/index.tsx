import { intl } from '@/utils/intl';
import {
  Col,
  Descriptions,
  Form,
  Modal,
  Row,
  Card,
  message,
} from '@oceanbase/design';
import React, { useEffect, useState } from 'react';
import { ExclamationCircleFilled } from '@ant-design/icons';
// import { Pie } from '@alipay/ob-charts';
import { minBy, find } from 'lodash';
import { useRequest } from 'ahooks';
import { Alert } from 'antd';
import { errorHandler } from '@/utils';
import * as Metadb from '@/services/ocp_installer_backend/Metadb';
import SliderAndInputNumber from '@/component/SliderAndInputNumber';
import { findBy } from '@oceanbase/util';
import styles from './index.less';

export interface ModifyResourcePoolModalProps {
  createMetadbDeployment: (params) => void;
  currentMetadbDeploymentConfig?: any;
  createMetadbData?: any;
  loading?: boolean;
  visible?: boolean;
  id: number;
}

const ModifyResourcePoolModal: React.FC<ModifyResourcePoolModalProps> = ({
  currentMetadbDeploymentConfig,
  createMetadbDeployment,
  createMetadbData,
  visible,
  loading,
  id,
  ...restProps
}) => {
  const [form] = Form.useForm();
  const { validateFields, setFieldsValue, getFieldValue } = form;

  // 剩余空间
  const [dataDirFreeSize, setDataDirFreeSize] = useState(0);
  const [logDirFreeSize, setLogDirFreeSize] = useState(0);

  const [maxDataDirDisk, setMaxDataDirDisk] = useState(0);
  const [maxLogSize, setMaxLogSize] = useState(0);

  const [memoryLimitSize, setMemoryLimitSize] = useState(1);
  const [dataFileSize, setDataFileSize] = useState(1);
  const [logDiskSize, setLogDiskSize] = useState(1);

  const [minMetadbResource, setMinMetadbResource] =
    useState<API.ObserverResource>();

  const [commonTenantReserve, setCommonTenantReserve] = useState(0);

  // 查询主机的资源
  const {
    data: metadbDeploymentResourceData,
    run: getMetadbDeploymentResource,
  } = useRequest(Metadb.getMetadbDeploymentResource, {
    manual: true,
    onSuccess: (res) => {
      if (res.success) {
        const metadbDeploymentResource = res?.data || {};
        if (metadbDeploymentResource?.items?.length === 0) {
          return message.warning(
            intl.formatMessage({
              id: 'OBD.Component.ModifyResourcePoolModal.NoResourcesFound',
              defaultMessage: '未查询到资源',
            }),
          );
        }

        const currentMinMetadbResource: API.ObserverResource = minBy(
          res?.data?.items,
          (item) => item?.memory_limit_higher_limit,
        );
        // 如果用户如有上次的手动输入，需要采用用户输入
        if (currentMetadbDeploymentConfig?.id) {
          const { parameters } = currentMetadbDeploymentConfig?.config;
          setFieldsValue({
            memory_limit: find(
              parameters,
              (item) => item?.name === 'memory_limit',
            )?.value?.split('G')[0],
            datafile_size: find(
              parameters,
              (item) => item?.name === 'datafile_size',
            )?.value?.split('G')[0],
            log_disk_size: find(
              parameters,
              (item) => item?.name === 'log_disk_size',
            )?.value?.split('G')[0],
          });
        } else {
          setFieldsValue({
            memory_limit: currentMinMetadbResource?.memory_limit_default,
            datafile_size: currentMinMetadbResource?.memory_limit_default * 3,
            log_disk_size: currentMinMetadbResource?.memory_limit_default * 3,
          });
        }

        setMemoryLimitSize(currentMinMetadbResource?.memory_limit_default);
        setMinMetadbResource(currentMinMetadbResource);

        const memoryLimitSizeMax =
          currentMinMetadbResource?.memory_limit_higher_limit -
          Math.ceil(currentMinMetadbResource?.memory_limit_higher_limit * 0.1) -
          Math.floor(currentMinMetadbResource?.memory_limit_higher_limit * 0.1);

        setCommonTenantReserve(
          memoryLimitSizeMax - currentMinMetadbResource?.memory_limit_default,
        );

        const { config } = createMetadbData;
        const data_dir = config?.data_dir || 'data/1';
        const log_dir = config?.log_dir || 'data/log';

        // 根据对应路径找到对应盘  取出相应盘的剩余空间
        const data_dir_disk = findBy(
          currentMinMetadbResource?.disk || [],
          'path',
          data_dir,
        );
        const log_dir_disk = findBy(
          currentMinMetadbResource?.disk || [],
          'path',
          log_dir,
        );

        const dataDirDiskInfoFreeSize = Number(
          data_dir_disk?.disk_info?.free_size,
        );
        const logDirDiskInfoFreeSize = Number(
          log_dir_disk?.disk_info?.free_size,
        );

        setDataDirFreeSize(dataDirDiskInfoFreeSize);
        setLogDirFreeSize(logDirDiskInfoFreeSize);

        setLimit(
          dataDirDiskInfoFreeSize,
          logDirDiskInfoFreeSize,
          currentMinMetadbResource?.data_size_default,
          currentMinMetadbResource?.log_size_default,
        );
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  const metadbResource = metadbDeploymentResourceData?.data || {};

  const setLimit = (
    dataDirDiskInfoFreeSize: number,
    logDirDiskInfoFreeSize: number,
    currentDataSize: number,
    currentLogSize: number,
  ) => {
    let data_size_limit = 0;
    let log_size_limit = 0;

    switch (
      minBy(metadbResource?.items, (item) => item?.memory_limit_higher_limit)
        ?.flag
    ) {
      case 1:
        data_size_limit = dataDirDiskInfoFreeSize - 2 - currentLogSize;
        log_size_limit = dataDirDiskInfoFreeSize - 2 - currentDataSize;
        break;
      case 2:
        data_size_limit = dataDirDiskInfoFreeSize - currentLogSize;
        log_size_limit = dataDirDiskInfoFreeSize - currentDataSize;
        break;
      case 3:
        data_size_limit = dataDirDiskInfoFreeSize - 2;
        log_size_limit = dataDirDiskInfoFreeSize - 2;
        break;
      case 4:
        data_size_limit = dataDirDiskInfoFreeSize * 0.9;
        log_size_limit = logDirDiskInfoFreeSize * 0.9;
        break;
      default:
        break;
    }

    setMaxDataDirDisk(data_size_limit);
    setMaxLogSize(log_size_limit);
  };

  useEffect(() => {
    if (id && visible) {
      getMetadbDeploymentResource({ id });
    }
  }, [id, visible]);

  const handleSubmit = () => {
    validateFields().then((values) => {
      const { datafile_size, log_disk_size } = values;

      if (createMetadbDeployment) {
        createMetadbDeployment({
          parameters: [
            {
              name: 'memory_limit',
              value: `${values?.memory_limit || memoryLimitSize}G`,
            },
            {
              name: 'datafile_size',
              value: `${datafile_size}G`,
            },
            {
              name: 'log_disk_size',
              value: `${log_disk_size}G`,
            },
          ],
        });
      }
    });
  };

  const memoryFreeGB = minMetadbResource?.memory_limit_higher_limit;

  const resourceList = [
    {
      type: intl.formatMessage({
        id: 'OBD.Component.ModifyResourcePoolModal.SystemPreOccupation',
        defaultMessage: '系统预占用',
      }),
      value: Math.ceil(memoryFreeGB * 0.1),
    },
    {
      type: 'memory_limit',
      value: memoryLimitSize,
    },
    {
      type: intl.formatMessage({
        id: 'OBD.Component.ModifyResourcePoolModal.OcpServiceReservation',
        defaultMessage: 'OCP 服务预留',
      }),
      value: Math.floor(memoryFreeGB * 0.1),
    },
    {
      type: intl.formatMessage({
        id: 'OBD.Component.ModifyResourcePoolModal.CommonTenantReservation',
        defaultMessage: '普通租户预留',
      }),
      value: commonTenantReserve,
    },
  ];

  const memoryLimitSizeMax =
    minMetadbResource?.memory_limit_higher_limit -
    Math.ceil(memoryFreeGB * 0.1) -
    Math.floor(memoryFreeGB * 0.1);
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
      width={666}
      title={intl.formatMessage({
        id: 'OBD.Component.ModifyResourcePoolModal.ResourceAllocation',
        defaultMessage: '资源分配',
      })}
      destroyOnClose={true}
      onOk={handleSubmit}
      visible={visible}
      confirmLoading={loading}
      {...restProps}
    >
      <Alert
        type="info"
        showIcon={true}
        message={intl.formatMessage({
          id: 'OBD.Component.ModifyResourcePoolModal.BasedOnTheMinimumAvailable',
          defaultMessage:
            '根据当前环境最小可用资源计算，建议为 MetaDB 分配的资源如下：',
        })}
        style={{
          height: 54,
          margin: '20px 0 16px',
        }}
      />

      <Form
        form={form}
        preserve={true}
        layout="vertical"
        hideRequiredMark={true}
        className={styles.resorcePollModal}
      >
        <Row gutter={[8, 12]}>
          <Col span={24}>
            <Card
              bordered={false}
              divided={false}
              className="card-background-color"
            >
              {/* <Descriptions
                 column={1}
                 title={<span style={{ fontSize: 14 }}>内存分配图（GiB）</span>}
                 style={{ marginBottom: 24 }}
                >
                 <Descriptions.Item>
                   <Pie height={100} {...config1} />
                 </Descriptions.Item>
                </Descriptions> */}
              <Form.Item
                style={{
                  width: '100%',
                  borderTop: '1px solid #E2E8F3',
                  paddingTop: 12,
                }}
                label="memory_limit"
                // label={
                //   <ContentWithQuestion
                //     content="memory_limit"
                //     tooltip={{
                //       title: 'OceanBase 系统预留内存大小，不能分配给租户使用',
                //     }}
                //   />
                // }
                name="memory_limit"
                initialValue={minMetadbResource?.memory_limit_default}
                // validateStatus={memoryLimitSizeMax < minMetadbResource?.memory_limit_default ? "warning" : ''}
              >
                <SliderAndInputNumber
                  min={
                    minMetadbResource?.memory_limit_lower_limit > 12
                      ? minMetadbResource?.memory_limit_lower_limit
                      : 12
                  }
                  // value={minMetadbResource?.memory_limit_default}
                  max={memoryLimitSizeMax}
                  onChange={(val) => {
                    setMemoryLimitSize(val);
                    setCommonTenantReserve(memoryLimitSizeMax - val);
                    setFieldsValue({
                      datafile_size: val * 3,
                      log_disk_size: val * 3,
                    });
                  }}
                />
              </Form.Item>
            </Card>
          </Col>
          <Col span={24}>
            <Card bordered={false} className="card-background-color">
              <Form.Item
                label={
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span>
                      {intl.formatMessage({
                        id: 'OBD.Component.ModifyResourcePoolModal.DataFile',
                        defaultMessage: '数据文件',
                      })}
                    </span>
                    {maxDataDirDisk < getFieldValue('memory_limit') * 3 && (
                      <div style={{ color: '#5C6B8A' }}>
                        <ExclamationCircleFilled
                          style={{ color: '#F7C02C', marginRight: 5 }}
                        />{' '}
                        {intl.formatMessage({
                          id: 'OBD.Component.ModifyResourcePoolModal.TheDataFileSpaceIs',
                          defaultMessage:
                            '数据文件空间不足，数据文件大小默认为 memory_limit 的 3 倍',
                        })}
                      </div>
                    )}
                  </div>
                }
                name="datafile_size"
                initialValue={getFieldValue('memory_limit') * 3}
                validateStatus={
                  maxDataDirDisk < getFieldValue('memory_limit') * 3
                    ? 'warning'
                    : ''
                }
              >
                <SliderAndInputNumber
                  min={getFieldValue('memory_limit') * 3}
                  max={maxDataDirDisk}
                  // value={minMetadbResource?.data_size_default}
                  onChange={(val) => {
                    setDataFileSize(val);
                    setLimit(dataDirFreeSize, logDirFreeSize, val, logDiskSize);
                  }}
                />
              </Form.Item>
            </Card>
          </Col>
          <Col span={24}>
            <Card bordered={false} className="card-background-color">
              <Form.Item
                label={
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span>
                      {intl.formatMessage({
                        id: 'OBD.Component.ModifyResourcePoolModal.LogFile',
                        defaultMessage: '日志文件',
                      })}
                    </span>
                    {maxLogSize < getFieldValue('memory_limit') * 3 ? (
                      <div style={{ color: '#5C6B8A' }}>
                        <ExclamationCircleFilled
                          style={{ color: '#F7C02C', marginRight: 5 }}
                        />
                        {intl.formatMessage({
                          id: 'OBD.Component.ModifyResourcePoolModal.TheLogFileHasInsufficient',
                          defaultMessage:
                            '日志文件空间不足，日志文件大小默认为 memory_limit 的 3 倍',
                        })}
                      </div>
                    ) : null}
                  </div>
                }
                name="log_disk_size"
                initialValue={getFieldValue('memory_limit') * 3}
                validateStatus={
                  maxLogSize < getFieldValue('memory_limit') * 3
                    ? 'warning'
                    : ''
                }
              >
                <SliderAndInputNumber
                  min={getFieldValue('memory_limit') * 3}
                  max={maxLogSize}
                  // value={minMetadbResource?.data_silog_size_defaultze_default}
                  onChange={(val) => {
                    setLogDiskSize(val);
                    setLimit(
                      dataDirFreeSize,
                      logDirFreeSize,
                      dataFileSize,
                      val,
                    );
                  }}
                />
              </Form.Item>
            </Card>
          </Col>
        </Row>
      </Form>
    </Modal>
  );
};

export default ModifyResourcePoolModal;
