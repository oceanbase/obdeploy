import ExitBtn from '@/component/ExitBtn';
import EnStyles from '@/pages/Obdeploy/indexEn.less';
import ZhStyles from '@/pages/Obdeploy/indexZh.less';
import { intl } from '@/utils/intl';
import {
  CheckCircleFilled,
  CloseCircleFilled,
  CloseOutlined,
  QuestionCircleFilled,
  ReadFilled,
} from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import {
  Button,
  Checkbox,
  Empty,
  Progress,
  Space,
  Spin,
  Tag,
  Timeline,
  Tooltip,
  Typography,
} from 'antd';
import NP from 'number-precision';
import { useEffect } from 'react';
import { getLocale } from 'umi';
import CustomFooter from '../CustomFooter';

interface PreCehckComponentProps {
  checkFinished: boolean;
  checkStatus: boolean;
  createLoading?: boolean;
  preCheckLoading: boolean;
  loading: boolean;
  hasManual: boolean;
  hasAuto: boolean;
  recoverLoading: boolean;
  precheckLoading?: boolean;
  errCodeLink: string;
  installLoading?: boolean;
  failedList: API.PreCheckInfo[];
  statusData: API.PreCheckResult;
  showFailedList: API.PreCheckInfo[];
  handleAutoRepair: () => void;
  handleRetryCheck: (parm?: any) => void;
  prevStep: () => void;
  handleInstall: () => void;
  handelCheck: () => void;
  setOnlyManual: React.Dispatch<React.SetStateAction<boolean>>;
  setIsScroll: React.Dispatch<React.SetStateAction<boolean>>;
  setIsScrollFailed: React.Dispatch<React.SetStateAction<boolean>>;
}

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

const { Text } = Typography;

const statusColorConfig = {
  PASSED: 'green',
  PENDING: 'gray',
  FAILED: 'red',
  SUCCESSFUL: 'green',
};

let timerScroll: NodeJS.Timer;
let timerFailed: NodeJS.Timer;
const initDuration = 3;
let durationScroll = initDuration;
let durationFailed = initDuration;
export default function PreCehckComponent({
  checkFinished,
  failedList,
  statusData,
  checkStatus,
  createLoading,
  preCheckLoading,
  errCodeLink,
  handleRetryCheck,
  loading,
  hasManual,
  setOnlyManual,
  handleAutoRepair,
  handelCheck,
  hasAuto,
  recoverLoading,
  showFailedList,
  prevStep,
  installLoading,
  handleInstall,
  setIsScroll,
  setIsScrollFailed,
}: PreCehckComponentProps) {
  const handleScrollTimeline = () => {
    if (!checkFinished) {
      setIsScroll(true);
      clearInterval(timerScroll);
      durationScroll = initDuration;
      timerScroll = setInterval(() => {
        if (durationScroll === 0) {
          clearInterval(timerScroll);
          setIsScroll(false);
          durationScroll = initDuration;
        } else {
          durationScroll -= 1;
        }
      }, 1000);
    }
  };

  const handleScrollFailed = () => {
    if (!checkFinished) {
      setIsScrollFailed(true);
      clearInterval(timerFailed);
      durationFailed = initDuration;
      timerFailed = setInterval(() => {
        if (durationFailed === 0) {
          clearInterval(timerFailed);
          setIsScrollFailed(false);
          durationFailed = initDuration;
        } else {
          durationFailed -= 1;
        }
      }, 1000);
    }
  };

  const handleAdvisement = (advisement: string | object | undefined) => {
    if (typeof advisement === 'object') return '';
    return advisement;
  };

  useEffect(() => {
    const timelineContainer = document.getElementById('timeline-container');
    timelineContainer.onmousewheel = handleScrollTimeline; // ie , chrome
    timelineContainer?.addEventListener('DOMMouseScroll', handleScrollTimeline); // firefox
    return () => {
      timelineContainer.onmousewheel = () => { };
      timelineContainer?.removeEventListener(
        'DOMMouseScroll',
        handleScrollTimeline,
      );
    };
  }, []);

  useEffect(() => {
    const addEventFailedContainer = () => {
      const failedContainer = document.getElementById('failed-container');
      if (failedList?.length && failedContainer) {
        if (!failedContainer.onmousewheel) {
          failedContainer.onmousewheel = handleScrollFailed; // ie , chrome
          failedContainer?.addEventListener(
            'DOMMouseScroll',
            handleScrollFailed,
          );
          // firefox
        }
      } else {
        setTimeout(() => {
          addEventFailedContainer();
        }, 3000);
      }
    };

    addEventFailedContainer();
    return () => {
      const failedContainer = document.getElementById('failed-container');
      if (failedContainer) {
        failedContainer.onmousewheel = () => { };
        failedContainer?.removeEventListener(
          'DOMMouseScroll',
          handleScrollFailed,
        );
      }
    };
  }, [failedList]);

  let progressStatus = 'active';
  if (statusData?.task_info?.status === 'FAILED') {
    progressStatus = 'exception';
  } else if (checkFinished) {
    if (statusData.all_passed) {
      progressStatus = 'success';
    } else {
      progressStatus = 'exception';
    }
  }

  const shape = (
    <div className={styles.shapeContainer}>
      <div className={styles.shape}></div>
      <div className={styles.shape}></div>
      <div className={styles.shape}></div>
      <div className={styles.shape}></div>
    </div>
  );

  const checkItemLength =
    !statusData?.finished && !statusData?.total
      ? null
      : `${statusData?.finished || 0}/${statusData?.total || 0}`;
  const failedItemLength = failedList?.length;
  return (
    <Space
      className={styles.spaceWidth}
      style={{ overflowX: 'hidden' }}
      direction="vertical"
      size="middle"
    >
      <ProCard
        title={
          checkStatus
            ? checkFinished
              ? intl.formatMessage({
                id: 'OBD.component.PreCheck.preCheck.CheckCompleted',
                defaultMessage: '检查完成',
              })
              : intl.formatMessage({
                id: 'OBD.component.PreCheck.preCheck.Checking',
                defaultMessage: '检查中',
              })
            : intl.formatMessage({
              id: 'OBD.component.PreCheck.preCheck.CheckFailed',
              defaultMessage: '检查失败',
            })
        }
        gutter={16}
        className="card-padding-bottom-24"
      >
        <ProCard
          title={intl.formatMessage(
            {
              id: 'OBD.component.PreCheck.preCheck.CheckItemCheckitemlength',
              defaultMessage: '检查项 {{checkItemLength}}',
            },
            { checkItemLength: checkItemLength },
          )}
          colSpan={12}
          className={`${styles.preCheckSubCard} card-padding-bottom-24 `}
          bodyStyle={{ overflowY: 'hidden' }}
          extra={
            <Button
              className={styles.preCheckBtn}
              disabled={
                checkStatus &&
                (!checkFinished || createLoading || preCheckLoading)
              }
              onClick={() => handleRetryCheck()}
              data-aspm-click="c307513.d317293"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.component.PreCheck.preCheck.PreCheckResultReCheck',
                defaultMessage: '预检查结果-重新检查',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.component.PreCheck.preCheck.ReCheck',
                defaultMessage: '重新检查',
              })}
            </Button>
          }
          headStyle={{ paddingLeft: '16px', paddingRight: '16px' }}
        >
          <Spin
            spinning={loading}
            style={{ width: 400, lineHeight: '300px' }}
          />

          {loading ? null : (
            <>
              <Progress
                className={styles.preCheckProgress}
                percent={
                  statusData?.finished
                    ? NP.times(
                      NP.divide(statusData?.finished, statusData?.total!),
                      100,
                    )
                    : 0
                }
                status={checkStatus ? progressStatus : 'exception'}
                showInfo={false}
              />

              <Timeline
                className={styles.timelineContainer}
                id="timeline-container"
              >
                {(statusData?.info || statusData?.task_info?.info)?.map(
                  (item: API.PreCheckInfo, index: number) => {
                    //根据索引找到对应项
                    const timelineData = statusData?.timelineData[index];
                    return (
                      <Timeline.Item
                        key={index}
                        id={`${timelineData?.isRunning ? 'running-timeline-item' : ''
                          }`}
                        color={statusColorConfig[timelineData?.result]}
                        dot={
                          timelineData?.result ? (
                            timelineData?.result === 'FAILED' ? (
                              <CloseCircleFilled style={{ fontSize: 10 }} />
                            ) : (
                              <CheckCircleFilled style={{ fontSize: 10 }} />
                            )
                          ) : null
                        }
                      >
                        {item?.name} {item?.server}
                      </Timeline.Item>
                    );
                  },
                )}
              </Timeline>
            </>
          )}
        </ProCard>
        <ProCard
          title={intl.formatMessage(
            {
              id: 'OBD.component.PreCheck.preCheck.FailedItemFaileditemlength',
              defaultMessage: '失败项 {{failedItemLength}}',
            },
            { failedItemLength: failedItemLength },
          )}
          split="horizontal"
          colSpan={12}
          className={styles.preCheckSubCard}
          headerBordered
          headStyle={{ paddingLeft: '16px', paddingRight: '16px' }}
          extra={
            <Space size={4}>
              {hasManual ? (
                <Checkbox
                  onChange={(e) => setOnlyManual(e.target.checked)}
                  disabled={!checkFinished || statusData?.all_passed}
                >
                  {intl.formatMessage({
                    id: 'OBD.component.PreCheck.preCheck.OnlyManualFixes',
                    defaultMessage: '只看手动修复项',
                  })}
                </Checkbox>
              ) : null}
              <Button
                className={
                  !checkFinished || !hasAuto
                    ? styles.disabledPreCheckBtn
                    : styles.preCheckBtn
                }
                type="primary"
                disabled={!checkFinished || !hasAuto}
                onClick={handleAutoRepair}
                // 修复回滚，引发检查列表问题
                // onClick={() => {
                //   handelCheck()
                //   handleAutoRepair()
                // }}
                loading={recoverLoading}
                data-aspm-click="c307513.d317292"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.component.PreCheck.preCheck.PreCheckResultAutomaticRepair',
                  defaultMessage: '预检查结果-自动修复',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.component.PreCheck.preCheck.AutomaticRepair',
                  defaultMessage: '自动修复',
                })}
              </Button>
            </Space>
          }
        >
          {showFailedList?.length ? (
            <div className={styles.failedContainer} id="failed-container">
              {showFailedList?.map((item, index) => {
                let reason = '',
                  responseReason =
                    item?.description ||
                    (handleAdvisement(item?.advisement) as string);
                if (responseReason) {
                  const index = responseReason.indexOf(':');
                  reason = responseReason.substring(
                    index,
                    responseReason.length,
                  );
                }
                return (
                  <Space
                    className={`${styles.spaceWidth} ${styles.failedItem}`}
                    size={4}
                    direction="vertical"
                    key={`${item.name}_${index}`}
                  >
                    <Text style={{ verticalAlign: 'top' }}>
                      <span
                        className={`${styles.iconContainer} ${styles.failedItemIcon} error-color mr-10 `}
                      >
                        <CloseOutlined className={styles.icon} />
                      </span>
                      {item.name}
                    </Text>
                    <Tooltip
                      title={
                        item.description || handleAdvisement(item?.advisement)
                      }
                      overlayClassName="list-tooltip"
                    >
                      <Text ellipsis>
                        <QuestionCircleFilled
                          className={`${styles.failedItemIcon} mr-10`}
                          style={{ color: '#8592ad', fontSize: '10px' }}
                        />
                        {intl.formatMessage({
                          id: 'OBD.component.PreCheck.preCheck.Reason',
                          defaultMessage: '原因：',
                        })}
                        <a href={errCodeLink} target="_blank">
                          OBD-{item.code}
                        </a>{' '}
                        {reason}
                      </Text>
                    </Tooltip>
                    <Tooltip
                      title={
                        item.advisement?.description ||
                        handleAdvisement(item?.advisement)
                      }
                      overlayClassName="list-tooltip"
                    >
                      <Text ellipsis>
                        <ReadFilled
                          className={`${styles.failedItemIcon} mr-10`}
                          style={{ color: '#8592ad', fontSize: '10px' }}
                        />
                        {intl.formatMessage({
                          id: 'OBD.component.PreCheck.preCheck.Suggestions',
                          defaultMessage: '建议：',
                        })}
                        {item.recoverable ? (
                          <Tag className="green-tag">
                            {intl.formatMessage({
                              id: 'OBD.component.PreCheck.preCheck.AutomaticRepair',
                              defaultMessage: '自动修复',
                            })}
                          </Tag>
                        ) : (
                          <Tag className="default-tag">
                            {intl.formatMessage({
                              id: 'OBD.component.PreCheck.preCheck.ManualRepair',
                              defaultMessage: '手动修复',
                            })}
                          </Tag>
                        )}{' '}
                        {item.advisement?.description ||
                          handleAdvisement(item?.advisement)}
                      </Text>
                      <br />
                      <a
                        className={styles.preCheckLearnMore}
                        href={errCodeLink}
                        target="_blank"
                      >
                        {intl.formatMessage({
                          id: 'OBD.component.PreCheck.preCheck.LearnMore',
                          defaultMessage: '了解更多方案',
                        })}
                      </a>
                    </Tooltip>
                  </Space>
                );
              })}
              {!checkFinished ? (
                <div style={{ marginLeft: 15 }}>{shape}</div>
              ) : null}
            </div>
          ) : checkFinished ? (
            <Empty
              image="/assets/empty.png"
              style={{ marginTop: '100px' }}
              description={
                <span style={{ color: '#8592ad' }}>
                  {intl.formatMessage({
                    id: 'OBD.component.EnvPreCheck.CheckFailuredItem.GreatCheckAllSuccessful',
                    defaultMessage: '太棒了！检查全部成功！',
                  })}
                </span>
              }
            />
          ) : (
            <div className={styles.preLoading}>
              {shape}
              <div className={styles.desc} style={{ color: '#8592ad' }}>
                {intl.formatMessage({
                  id: 'OBD.component.PreCheck.preCheck.NoFailedItemsFoundYet',
                  defaultMessage: '暂未发现失败项',
                })}
              </div>
            </div>
          )}
        </ProCard>
      </ProCard>
      <CustomFooter>
        {' '}
        <ExitBtn />
        <Button onClick={prevStep} disabled={checkStatus && !checkFinished}>
          {intl.formatMessage({
            id: 'OBD.component.PreCheck.preCheck.PreviousStep',
            defaultMessage: '上一步',
          })}
        </Button>
        {!statusData?.all_passed ? (
          <Tooltip
            title={intl.formatMessage({
              id: 'OBD.component.PreCheck.preCheck.FixAllFailedItems',
              defaultMessage: '请修复全部失败项',
            })}
          >
            <Button type="primary" disabled={true}>
              {intl.formatMessage({
                id: 'OBD.component.PreCheck.preCheck.NextStep',
                defaultMessage: '下一步',
              })}
            </Button>
          </Tooltip>
        ) : (
          <Button
            type="primary"
            loading={installLoading}
            onClick={handleInstall}
          >
            {intl.formatMessage({
              id: 'OBD.component.PreCheck.preCheck.Deployment',
              defaultMessage: '部署',
            })}
          </Button>
        )}
      </CustomFooter>
    </Space>
  );
}
