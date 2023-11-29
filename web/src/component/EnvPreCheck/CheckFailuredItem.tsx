import { intl } from '@/utils/intl';
import React, { useState } from 'react';
import {
  Button,
  Space,
  Checkbox,
  Typography,
  Tag,
  Spin,
} from '@oceanbase/design';
import {
  CloseCircleFilled,
  QuestionCircleFilled,
  ReadFilled,
} from '@ant-design/icons';
import { findByValue } from '@oceanbase/util';
import { useRequest } from 'ahooks';
import { errorHandler } from '@/utils';
import * as Metadb from '@/services/ocp_installer_backend/Metadb';
import { ERROR_CODE_LIST } from '@/constant/envPresCheck';
import Prechecked from '@/component/Icon/Prechecked';
import styles from './index.less';
const { Text } = Typography;

export interface CheckFailuredItemProps {
  id?: number;
  loading?: boolean;
  precheckMetadbResult: any;
  onSuccess?: () => void;
}

const CheckFailuredItem: React.FC<CheckFailuredItemProps> = ({
  id,
  loading,
  onSuccess,
  precheckMetadbResult,
}) => {
  let precheckStatus;
  // const { precheckStatus } = useSelector((state: DefaultRootState) => state.global);
  const precheck_failed_list =
    precheckMetadbResult?.precheck_result?.filter(
      (item) => item.result === 'FAILED',
    ) || [];

  const [precheckFailedList, setlrecheckFailedList] =
    useState<[]>(precheck_failed_list);

  const { runAsync: recoverMetadbDeployment } = useRequest(
    Metadb.recoverMetadbDeployment,
    {
      manual: true,
      onSuccess: (res) => {
        if (res?.success && onSuccess) {
          onSuccess();
        }
      },
      onError: ({ response, data }: any) => {
        errorHandler({ response, data });
      },
    },
  );

  // recoverable: false 手动
  // recoverable: true 自动
  const onChange = (e: CheckboxChangeEvent) => {
    setlrecheckFailedList(
      e?.target?.checked
        ? precheck_failed_list.filter((item) => item.recoverable === false)
        : precheck_failed_list,
    );
  };

  return (
    <div className={styles.checkItem}>
      <Space className={styles.checkItemTitle}>
        <span>{`失败项 ${precheck_failed_list.length}/${
          precheckMetadbResult?.precheck_result?.length || 0
        }`}</span>
        <Space>
          {precheckStatus === 'RUNNING' ? null : (
            <Checkbox onChange={onChange}>
              {intl.formatMessage({
                id: 'OBD.component.EnvPreCheck.CheckFailuredItem.OnlyManualFixes',
                defaultMessage: '只看手动修复项',
              })}
            </Checkbox>
          )}

          <Button
            data-aspm="c323721"
            data-aspm-desc={intl.formatMessage({
              id: 'OBD.component.EnvPreCheck.CheckFailuredItem.AutomaticRepair',
              defaultMessage: '自动修复',
            })}
            data-aspm-param={``}
            data-aspm-expo
            type="primary"
            disabled={
              precheckStatus === 'RUNNING' ||
              precheckFailedList.filter((item) => item?.recoverable).length ===
                0
            }
            onClick={() => {
              recoverMetadbDeployment({
                id,
              });
            }}
          >
            {intl.formatMessage({
              id: 'OBD.component.EnvPreCheck.CheckFailuredItem.AutomaticRepair',
              defaultMessage: '自动修复',
            })}
          </Button>
        </Space>
      </Space>
      <>
        {precheckFailedList.length === 0 || loading ? (
          <div>
            {precheckStatus === 'RUNNING' && (
              <div style={{ paddingTop: '40%' }}>
                <Spin
                  tip={intl.formatMessage({
                    id: 'OBD.component.EnvPreCheck.CheckFailuredItem.NoFailedItemsFoundYet',
                    defaultMessage: '暂未发现失败项',
                  })}
                >
                  <div />
                </Spin>
              </div>
            )}

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {precheckStatus === 'FINISHED' &&
                precheckMetadbResult?.task_info?.result === 'SUCCESSFUL' && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexDirection: 'column',
                      paddingTop: 100,
                    }}
                  >
                    <Prechecked size={120} />
                    <div style={{ fontSize: 14, color: ' #8592AD' }}>
                      {intl.formatMessage({
                        id: 'OBD.component.EnvPreCheck.CheckFailuredItem.GreatCheckAllSuccessful',
                        defaultMessage: '太棒了！检查全部成功！',
                      })}
                    </div>
                  </div>
                )}
            </div>
          </div>
        ) : (
          <>
            {precheckFailedList.map((item: API.PreCheckResult) => (
              <div className={styles.checkFailuredContent} key={item?.name}>
                <Space>
                  <CloseCircleFilled style={{ color: '#FF4D67' }} />
                  {`目录空间（${item?.name}）`}
                </Space>
                <div className={styles.checkFailuredItem}>
                  <Space style={{ width: 66 }}>
                    <QuestionCircleFilled style={{ color: '#8592AD' }} />
                    {intl.formatMessage({
                      id: 'OBD.component.EnvPreCheck.CheckFailuredItem.Reason',
                      defaultMessage: '原因：',
                    })}
                  </Space>
                  <Text
                    ellipsis={{
                      tooltip: findByValue(ERROR_CODE_LIST, item.code).label,
                    }}
                  >
                    <a
                      style={{ marginRight: 10 }}
                      target="_blank"
                      href="https://www.oceanbase.com/product/ob-deployer/error-codes"
                    >
                      {`ERR-${item.code}`}
                    </a>
                    {findByValue(ERROR_CODE_LIST, item.code).label}
                  </Text>
                </div>
                <div className={styles.checkFailuredItem}>
                  <Space style={{ width: 66 }}>
                    <ReadFilled style={{ color: '#8592AD' }} />
                    {intl.formatMessage({
                      id: 'OBD.component.EnvPreCheck.CheckFailuredItem.Suggestions',
                      defaultMessage: '建议：',
                    })}
                  </Space>
                  <Text ellipsis={{ tooltip: item.advisement }}>
                    {item.recoverable ? (
                      <Tag color="green">
                        {intl.formatMessage({
                          id: 'OBD.component.EnvPreCheck.CheckFailuredItem.AutomaticRepair',
                          defaultMessage: '自动修复',
                        })}
                      </Tag>
                    ) : (
                      <Tag>
                        {intl.formatMessage({
                          id: 'OBD.component.EnvPreCheck.CheckFailuredItem.ManualRepair',
                          defaultMessage: '手动修复',
                        })}
                      </Tag>
                    )}
                    {item.advisement}
                  </Text>
                </div>
                <a
                  style={{ marginLeft: 66 }}
                  target="_blank"
                  href="https://www.oceanbase.com/product/ob-deployer/error-codes"
                >
                  {intl.formatMessage({
                    id: 'OBD.component.EnvPreCheck.CheckFailuredItem.LearnMore',
                    defaultMessage: '了解更多方案',
                  })}
                </a>
              </div>
            ))}
            {precheckStatus === 'RUNNING' ||
              (loading && <Spin spinning={true} />)}
          </>
        )}
      </>
    </div>
  );
};

export default CheckFailuredItem;
