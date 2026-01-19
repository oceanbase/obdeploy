import CheckBadge from '@/component/CheckBadge';
import { OCP_UPGRADE_STATUS_LIST } from '@/constant/index';
import { intl } from '@/utils/intl';
import {
  Button,
  Card,
  Table,
} from 'antd';
import { find } from 'lodash';
import React, { useEffect, useState } from 'react';


export interface UpdatePreCheckProps {
  omsUpgradePrecheckTask?: any;
  precheckOmsUpgradeLoading?: boolean;
  refreshPrecheckOmsUpgrade?: () => void;
}

const UpdatePreCheck: React.FC<UpdatePreCheckProps> = ({
  omsUpgradePrecheckTask,
  refreshPrecheckOmsUpgrade,
  precheckOmsUpgradeLoading
}) => {
  const [omsUpgradePrecheckResult, setomsUpgradePrecheckResult] = useState(
    omsUpgradePrecheckTask?.precheck_result,
  );

  useEffect(() => {
    setomsUpgradePrecheckResult(omsUpgradePrecheckTask?.precheck_result);
  }, [omsUpgradePrecheckTask]);

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
      dataIndex: 'description',
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
      <Card
        bordered={false}
        title={`${omsUpgradePrecheckTask?.task_info?.result === 'FAILED' ?
          intl.formatMessage({
            id: 'OBD.component.PreCheck.preCheck.CheckFailed',
            defaultMessage: '检查失败',
          })
          :
          omsUpgradePrecheckTask?.task_info?.result === 'SUCCESSFUL' ?
            intl.formatMessage({
              id: 'OBD.component.PreCheck.preCheck.CheckCompleted',
              defaultMessage: '检查完成',
            })
            :
            intl.formatMessage({
              id: 'OBD.component.PreCheck.preCheck.Checking',
              defaultMessage: '检查中',
            })
          }`}
        extra={
          <Button
            type="primary"
            onClick={() => {
              refreshPrecheckOmsUpgrade();
            }}
            disabled={omsUpgradePrecheckTask?.task_info?.result === 'RUNNING' || precheckOmsUpgradeLoading}
          >
            {intl.formatMessage({
              id: 'OBD.Component.UpdatePreCheck.ReCheck',
              defaultMessage: '重新检查',
            })}
          </Button>
        }
      >
        <div
          style={{
            borderRadius: 8,
            border: '1px solid #CDD5E4',
            overflow: 'hidden',
          }}
        >
          <Table
            columns={columns}
            pagination={false}
            dataSource={omsUpgradePrecheckResult}
          />
        </div>
      </Card>
    </div>
  );
};

export default UpdatePreCheck;
