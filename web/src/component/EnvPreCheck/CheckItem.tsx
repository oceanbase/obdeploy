import { intl } from '@/utils/intl';
import React, { useEffect, useState } from 'react';
import { Button, Progress } from '@oceanbase/design';
import { Timeline } from 'antd';
import {
  CheckCircleTwoTone,
  CloseCircleTwoTone,
  LoadingOutlined,
} from '@ant-design/icons';
import NP from 'number-precision';
import styles from './index.less';

export interface CheckItemProps {
  precheckMetadbResult?: API.PrecheckTaskInfo;
  refresh?: () => void;
}

const statusColorConfig = {
  PASSED: 'green',
  PENDING: 'gray',
  FAILED: 'red',
};

const CheckItem: React.FC<CheckItemProps> = ({
  refresh,
  precheckMetadbResult,
}) => {
  // const { precheckStatus } = useSelector((state: DefaultRootState) => state.global);
  let precheckStatus;

  const [currentPrecheckMetadbResult, setCurrentPrecheckMetadbResult] =
    useState(precheckMetadbResult || {});

  const total = precheckMetadbResult?.precheck_result?.length || 0;
  const passedCount =
    precheckMetadbResult?.precheck_result?.filter(
      (item) => item.result === 'PASSED',
    ).length || 0;
  const currentPassedCount =
    currentPrecheckMetadbResult?.precheck_result?.filter(
      (item) => item.result === 'PASSED',
    ).length || 0;

  useEffect(() => {
    if (passedCount !== currentPassedCount) {
      setCurrentPrecheckMetadbResult(precheckMetadbResult);
    }
    if (precheckStatus === 'RUNNING') {
      setTimeout(() => {
        const timelineContainer = document.getElementById('timeline-container');
        const runningItemDom = document.getElementById('running-timeline-item');
        if (timelineContainer) {
          timelineContainer.scrollTop = NP.minus(
            NP.strip(runningItemDom?.offsetTop),
            150,
          );
        }
      }, 10);
    }
  }, [precheckStatus, passedCount]);

  const renderTimelineItemsIcon = (result?: string) => {
    switch (result) {
      case 'PASSED':
        return (
          <CheckCircleTwoTone style={{ color: '#0ac185', fontSize: 12 }} />
        );
      case 'FAILED':
        return <CloseCircleTwoTone style={{ color: 'red', fontSize: 12 }} />;
      default:
        return <LoadingOutlined />;
    }
  };

  return (
    <div className={styles.checkItem}>
      <div className={styles.checkItemTitle}>
        <span>
          {intl.formatMessage(
            {
              id: 'OBD.component.EnvPreCheck.CheckItem.CheckItemPassedcountTotal',
              defaultMessage: '检查项 {{passedCount}}/{{total}}',
            },
            { passedCount: passedCount, total: total },
          )}
        </span>
        <Button
          data-aspm="c323722"
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.component.EnvPreCheck.CheckItem.ReCheck',
            defaultMessage: '重新检查',
          })}
          data-aspm-param={``}
          data-aspm-expo
          disabled={precheckStatus === 'RUNNING'}
          onClick={refresh}
        >
          {intl.formatMessage({
            id: 'OBD.component.EnvPreCheck.CheckItem.ReCheck',
            defaultMessage: '重新检查',
          })}
        </Button>
      </div>

      <div className={styles.checnProgress}>
        <Progress
          size="small"
          showInfo={false}
          percent={NP.times(NP.divide(passedCount, total), 100)}
          strokeColor={{ '0': '#006aff', '50%': '#3fe6fc', '100%': '#006aff' }}
        />
      </div>
      <Timeline className={styles.checkSteps} id="timeline-container">
        {currentPrecheckMetadbResult?.precheck_result?.map(
          (item: any, index: number) => (
            <Timeline.Item
              id={`${
                currentPrecheckMetadbResult?.precheck_result[index - 1]
                  ?.result === 'RUNNING'
                  ? 'running-timeline-item'
                  : ''
              }`}
              color={statusColorConfig[item.result]}
              dot={
                item?.result === 'RUNNING'
                  ? null
                  : renderTimelineItemsIcon(item?.result)
              }
            >
              {item?.name} {item?.server}
            </Timeline.Item>
          ),
        )}
      </Timeline>
    </div>
  );
};

export default CheckItem;
