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
  ocpUpgradePrecheckTask?: any;
  getOcpInfoLoading?: boolean;
  precheckOcpUpgradeLoading?: boolean;
  changePrecheckNoPassed?: (val: boolean) => void;
}

const UpdatePreCheck: React.FC<UpdatePreCheckProps> = ({
  refresh,
  getOcpInfoLoading,
  ocpUpgradePrecheckTask,
  changePrecheckNoPassed,
  precheckOcpUpgradeLoading,
}) => {
  const [ocpUpgradePrecheckResult, setOcpUpgradePrecheckResult] = useState(
    ocpUpgradePrecheckTask?.precheck_result,
  );

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
        <Card
          bordered={false}
          title={`${precheckOcpUpgradeStatus === 'RUNNING'
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
            {precheckOcpUpgradeResultFaild?.length > 0 && (
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
      </Spin>
    </div>
  );
};

export default UpdatePreCheck;
