import CheckBadge from '@/component/CheckBadge';
import ArrowIcon from '@/component/Icon/ArrowIcon';
import NewIcon from '@/component/Icon/NewIcon';
import { OCP_UPGRADE_STATUS_LIST } from '@/constant/index';
import { intl } from '@/utils/intl';
import { ProCard } from '@ant-design/pro-components';
import {
  Alert,
  Button,
  Card,
  Col,
  Popconfirm,
  Row,
  Space,
  Spin,
  Table,
  Tooltip,
} from 'antd';
import { find } from 'lodash';
import React, { useEffect, useState } from 'react';
import { useModel } from 'umi';
import styles from './index.less';

export interface UpdatePreCheckProps {
  refresh?: () => void;
  updateInfo?: API.connectMetaDB;
  ocpUpgradePrecheckTask?: any;
  getOcpInfoLoading?: boolean;
  precheckOcpUpgradeLoading?: boolean;
  changePrecheckNoPassed?: (val: boolean) => void;
  cluster_name: string;
}

const UpdatePreCheck: React.FC<UpdatePreCheckProps> = ({
  refresh,
  updateInfo,
  getOcpInfoLoading,
  ocpUpgradePrecheckTask,
  changePrecheckNoPassed,
  precheckOcpUpgradeLoading,
  cluster_name,
}) => {
  const [ocpUpgradePrecheckResult, setOcpUpgradePrecheckResult] = useState(
    ocpUpgradePrecheckTask?.precheck_result,
  );
  const { ocpConfigData, DOCS_SOP } = useModel('global');
  const version: string = ocpConfigData?.components?.ocpserver?.version;
  const precheckOcpUpgradeStatus = ocpUpgradePrecheckTask?.task_info?.status;

  const precheckOcpUpgradeResultFaild =
    ocpUpgradePrecheckTask?.precheck_result?.filter(
      (item) => item.result === 'FAILED',
    );

  useEffect(() => {
    setOcpUpgradePrecheckResult(ocpUpgradePrecheckTask?.precheck_result);
  }, [ocpUpgradePrecheckTask]);

  const columns = [
    {
      title: intl.formatMessage({
        id: 'OBD.Component.UpdatePreCheck.CheckItems',
        defaultMessage: '检查项',
      }),
      dataIndex: 'name',
      width: '30%',
    },
    {
      title: intl.formatMessage({
        id: 'OBD.Component.UpdatePreCheck.CheckStatus',
        defaultMessage: '检查状态',
      }),
      dataIndex: 'result',
      width: 120,
      filters: OCP_UPGRADE_STATUS_LIST.map((item) => ({
        text: item.label,
        value: item.value,
      })),
      onFilter: (value: string, record: API.PrecheckResult) =>
        record.result === value,
      render: (text: string, record: API.PrecheckResult) => {
        const statusItem = find(
          OCP_UPGRADE_STATUS_LIST,
          (item) => item.value === text,
        );

        return (
          <CheckBadge
            text={statusItem?.label}
            status={statusItem?.badgeStatus}
          />
        );
      },
    },
    {
      title: intl.formatMessage({
        id: 'OBD.Component.UpdatePreCheck.Impact',
        defaultMessage: '影响',
      }),
      dataIndex: 'advisement',
      render: (text) => (text ? text : '-'),
    },
  ];

  return (
    <div
      data-aspm="c323725"
      data-aspm-desc={intl.formatMessage({
        id: 'OBD.Component.UpdatePreCheck.UpgradeEnvironmentPreCheckPage',
        defaultMessage: '升级环境预检查页',
      })}
      data-aspm-param={``}
      data-aspm-expo
      style={{ paddingBottom: 70 }}
    >
      <Spin spinning={getOcpInfoLoading || precheckOcpUpgradeLoading}>
        {!ocpUpgradePrecheckTask ? (
          <>
            <Alert
              type="info"
              showIcon={true}
              message=""
              description={intl.formatMessage({
                id: 'OBD.Component.UpdatePreCheck.BasedOnTheMetadbConfiguration',
                defaultMessage:
                  '根据 MetaDB 配置信息，成功获取 OCP 相关配置信息，为保证管理功能一致性，升级程序将升级平台管理服务（OCP Server） 及其管理的所有主机代理服务（OCP Agent），请检查并确认以下配置信息，确定后开始预检查',
              })}
              style={{
                margin: '16px 0',
              }}
            />

            <ProCard
              title={intl.formatMessage({
                id: 'OBD.Component.UpdatePreCheck.InstallationConfiguration',
                defaultMessage: '安装配置',
              })}
              className="card-padding-bottom-24"
            >
              <Col span={12}>
                <ProCard className={styles.infoSubCard} split="vertical">
                  <ProCard
                    colSpan={10}
                    title={intl.formatMessage({
                      id: 'OBD.Component.UpdatePreCheck.ClusterName',
                      defaultMessage: '集群名称',
                    })}
                  >
                    {cluster_name}
                  </ProCard>
                  <ProCard
                    colSpan={14}
                    title={intl.formatMessage({
                      id: 'OBD.Component.UpdatePreCheck.UpgradeType',
                      defaultMessage: '升级类型',
                    })}
                  >
                    {intl.formatMessage({
                      id: 'OBD.Component.UpdatePreCheck.UpgradeAll',
                      defaultMessage: '全部升级',
                    })}
                  </ProCard>
                </ProCard>
              </Col>
            </ProCard>
            <Card
              loading={getOcpInfoLoading}
              title={intl.formatMessage({
                id: 'OBD.Component.UpdatePreCheck.UpgradeConfigurationInformation',
                defaultMessage: '升级配置信息',
              })}
              bordered={false}
              divided={false}
              bodyStyle={{
                paddingBottom: 24,
              }}
            >
              <Row gutter={[24, 16]}>
                <Col span={24}>
                  <div className={styles.ocpVersion}>
                    {intl.formatMessage({
                      id: 'OBD.Component.UpdatePreCheck.PreUpgradeVersion',
                      defaultMessage: '升级前版本：',
                    })}
                    <span>V {updateInfo?.ocp_version}</span>
                  </div>
                  <div
                    style={{
                      float: 'left',
                      margin: '0 45px',
                      textAlign: 'center',
                      lineHeight: '69px',
                    }}
                  >
                    <ArrowIcon height={30} width={42} />
                  </div>
                  <div className={styles.ocpVersion}>
                    {intl.formatMessage({
                      id: 'OBD.Component.UpdatePreCheck.UpgradedVersion',
                      defaultMessage: '升级后版本：',
                    })}

                    <span>V {version}</span>
                    <NewIcon
                      size={36}
                      style={{
                        position: 'relative',
                        top: -12,
                      }}
                    />
                  </div>
                </Col>
              </Row>
              <div
                style={{
                  marginTop: 24,
                  borderRadius: 8,
                  border: '1px solid #CDD5E4',
                  overflow: 'hidden',
                }}
              >
                <Table
                  loading={getOcpInfoLoading}
                  columns={[
                    {
                      title: intl.formatMessage({
                        id: 'OBD.Component.UpdatePreCheck.ComponentName',
                        defaultMessage: '组件名称',
                      }),
                      dataIndex: 'name',
                      width: '20%',
                    },
                    {
                      title: intl.formatMessage({
                        id: 'OBD.Component.UpdatePreCheck.NodeIp',
                        defaultMessage: '节点 IP',
                      }),
                      dataIndex: 'ip',
                      render: (ip, record) => {
                        if (!ip || ip === '') {
                          return '-';
                        }
                        return ip.map((item: string) => <span>{item} </span>);
                      },
                    },
                  ]}
                  rowKey="name"
                  pagination={false}
                  dataSource={
                    updateInfo?.component ? updateInfo?.component : []
                  }
                />
              </div>
              {updateInfo?.tips && (
                <p style={{ color: '#8592AD', fontSize: 14, fontWeight: 400 }}>
                  {intl.formatMessage({
                    id: 'OBD.Component.UpdatePreCheck.MetadbSharesMetaTenantResources',
                    defaultMessage:
                      'MetaDB与MonitorDB共享Meta租户资源，容易造成OCP运行异常，强烈建议您新建Monitor租户，并进行MetaDB数据清理和MonitorDB数据迁移，详情请参考《',
                  })}
                  <a href={DOCS_SOP} target="_blank">
                    SOP
                  </a>
                  》
                </p>
              )}
            </Card>
          </>
        ) : (
          <Card
            bordered={false}
            title={`${
              precheckOcpUpgradeStatus === 'RUNNING'
                ? intl.formatMessage({
                    id: 'OBD.component.PreCheck.preCheck.Checking',
                    defaultMessage: '检查中',
                  })
                : intl.formatMessage({
                    id: 'OBD.component.PreCheck.preCheck.CheckCompleted',
                    defaultMessage: '检查完成',
                  })
            }`}
          >
            <div
              style={{
                borderRadius: 8,
                border: '1px solid #CDD5E4',
                overflow: 'hidden',
              }}
            >
              <Table
                loading={precheckOcpUpgradeLoading}
                columns={columns}
                pagination={false}
                dataSource={ocpUpgradePrecheckResult}
              />
            </div>
            <Space
              style={{
                position: 'relative',
                left: '50%',
                marginTop: 24,
                transform: 'translateX(-50%)',
              }}
            >
              {precheckOcpUpgradeResultFaild.length > 0 && (
                <Popconfirm
                  title={intl.formatMessage({
                    id: 'OBD.Component.UpdatePreCheck.AreYouSureYouWant',
                    defaultMessage: '确认要忽略所有未通过的检查项吗？',
                  })}
                  onConfirm={() => {
                    setOcpUpgradePrecheckResult(
                      ocpUpgradePrecheckResult?.map((item) => ({
                        ...item,
                        result:
                          item?.result === 'FAILED' ? 'IGNORED' : item?.result,
                      })),
                    );
                    if (changePrecheckNoPassed) {
                      changePrecheckNoPassed(false);
                    }
                  }}
                >
                  <Button
                    data-aspm="c323724"
                    data-aspm-desc={intl.formatMessage({
                      id: 'OBD.Component.UpdatePreCheck.UpgradeIgnoresAllFailedItems',
                      defaultMessage: '升级忽略全部未通过项',
                    })}
                    data-aspm-param={``}
                    data-aspm-expo
                  >
                    {intl.formatMessage({
                      id: 'OBD.Component.UpdatePreCheck.IgnoreAllFailedItems',
                      defaultMessage: '忽略全部未通过项',
                    })}
                  </Button>
                </Popconfirm>
              )}

              <Tooltip
                title={
                  precheckOcpUpgradeStatus === 'RUNNING' &&
                  intl.formatMessage({
                    id: 'OBD.Component.UpdatePreCheck.PreCheckIsInProgress',
                    defaultMessage: '预检查进行中，暂不支持重新检查',
                  })
                }
              >
                <Button
                  data-aspm="c323723"
                  data-aspm-desc={intl.formatMessage({
                    id: 'OBD.Component.UpdatePreCheck.UpgradeAndReCheck',
                    defaultMessage: '升级重新检查',
                  })}
                  data-aspm-param={``}
                  data-aspm-expo
                  disabled={precheckOcpUpgradeStatus === 'RUNNING'}
                  onClick={() => {
                    if (refresh) {
                      refresh();
                    }
                  }}
                >
                  {intl.formatMessage({
                    id: 'OBD.Component.UpdatePreCheck.ReCheck',
                    defaultMessage: '重新检查',
                  })}
                </Button>
              </Tooltip>
            </Space>
          </Card>
        )}
      </Spin>
    </div>
  );
};

export default UpdatePreCheck;
