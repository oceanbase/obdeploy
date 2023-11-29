import { intl } from '@/utils/intl';
import { useEffect, useState } from 'react';
import { useModel } from 'umi';
import {
  Space,
  Button,
  Progress,
  Timeline,
  Checkbox,
  Typography,
  Tooltip,
  Tag,
  Spin,
  message,
  Empty,
} from 'antd';
import { ProCard } from '@ant-design/pro-components';
import {
  CloseOutlined,
  QuestionCircleFilled,
  ReadFilled,
  CheckCircleFilled,
  CloseCircleFilled,
} from '@ant-design/icons';
import useRequest from '@/utils/useRequest';
import {
  preCheck,
  preCheckStatus,
  deployAndStartADeployment,
  createDeploymentConfig,
  recover,
} from '@/services/ob-deploy-web/Deployments';
import { handleQuit, getErrorInfo } from '@/utils';
import NP from 'number-precision';
import { getLocale } from 'umi';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

const { Text } = Typography;

const statusColorConfig = {
  PASSED: 'green',
  PENDING: 'gray',
  FAILED: 'red',
};

let timerScroll: NodeJS.Timer;
let timerFailed: NodeJS.Timer;
const initDuration = 3;
let durationScroll = initDuration;
let durationFailed = initDuration;

const errCodeUrl = 'https://www.oceanbase.com/product/ob-deployer/error-codes';

export default function PreCheckStatus() {
  const {
    setCurrentStep,
    configData,
    setCheckOK,
    handleQuitProgress,
    getInfoByName,
    setConfigData,
    setErrorVisible,
    setErrorsList,
    errorsList,
  } = useModel('global');
  const oceanbase = configData?.components?.oceanbase;
  const name = configData?.components?.oceanbase?.appname;
  const [statusData, setStatusData] = useState<API.PreCheckResult>({});
  const [failedList, setFailedList] = useState<API.PreCheckInfo[]>([]);
  const [showFailedList, setShowFailedList] = useState<API.PreCheckInfo[]>([]);
  const [hasAuto, setHasAuto] = useState(false);
  const [hasManual, setHasManual] = useState(false);
  const [onlyManual, setOnlyManual] = useState(false);
  const [checkFinished, setCheckFinished] = useState(false);
  const [isScroll, setIsScroll] = useState(false);
  const [isScrollFailed, setIsScrollFailed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [checkStatus, setCheckStatus] = useState(true);
  const [currentPage, setCurrentPage] = useState(true);
  const [firstErrorTimestamp, setFirstErrorTimestamp] = useState<number>();

  const { run: fetchPreCheckStatus } = useRequest(preCheckStatus, {
    onSuccess: ({ success, data }: API.OBResponsePreCheckResult_) => {
      if (success) {
        let timer: NodeJS.Timer;
        setStatusData(data || {});
        if (data?.status === 'RUNNING') {
          timer = setTimeout(() => {
            fetchPreCheckStatus({ name });
          }, 1000);
        }
        if (data?.status === 'FAILED') {
          let errorInfo: API.ErrorInfo = {
            title: intl.formatMessage({
              id: 'OBD.pages.components.PreCheckStatus.RequestError',
              defaultMessage: '请求错误',
            }),
            desc: data?.message,
          };
          setErrorVisible(true);
          setErrorsList([...errorsList, errorInfo]);
          setCheckStatus(false);
        } else {
          if (data?.all_passed) {
            setFailedList([]);
            setShowFailedList([]);
          } else {
            const newFailedList =
              data?.info?.filter((item) => item.result === 'FAILED') || [];
            newFailedList.forEach((item) => {
              if (item.recoverable) {
                setHasAuto(true);
              } else {
                setHasManual(true);
              }
            });
            setFailedList(newFailedList);
            setShowFailedList(newFailedList);
          }
          const isFinished = !!data?.total && data?.finished === data?.total;
          setCheckFinished(isFinished);
          if (isFinished) {
            clearTimeout(timer);
          }
          if (!isScroll && !isFinished) {
            setTimeout(() => {
              const timelineContainer =
                document.getElementById('timeline-container');
              const runningItemDom = document.getElementById(
                'running-timeline-item',
              );

              timelineContainer.scrollTop = NP.minus(
                NP.strip(runningItemDom?.offsetTop),
                150,
              );
            }, 10);
          }

          if (!isScrollFailed && !isFinished && failedList) {
            setTimeout(() => {
              const failedContainer =
                document.getElementById('failed-container');
              if (failedContainer) {
                failedContainer.scrollTop = NP.strip(
                  failedContainer?.scrollHeight,
                );
              }
            }, 10);
          }
          setCheckStatus(true);
        }
        if (loading) {
          setLoading(false);
        }
      }
    },
    onError: ({ response, data, type }: any) => {
      const handleError = () => {
        const errorInfo = getErrorInfo({ response, data, type });
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      };
      if (response?.status === 504 || (!response && type === 'TypeError')) {
        const nowTime = Date.now();
        if (!firstErrorTimestamp) {
          setFirstErrorTimestamp(nowTime);
        }
        if (NP.divide(nowTime - firstErrorTimestamp) > 60000) {
          handleError();
          setCheckStatus(false);
          if (loading) {
            setLoading(false);
          }
        } else {
          if (currentPage) {
            setTimeout(() => {
              fetchPreCheckStatus({ name });
            }, 1000);
          }
        }
      } else {
        handleError();
      }
    },
  });

  const { run: handlePreCheck, loading: preCheckLoading } = useRequest(
    preCheck,
    {
      onSuccess: ({ success }: API.OBResponse) => {
        if (success) {
          handleStartCheck();
        }
      },
      onError: (e: any) => {
        setCheckStatus(false);
        if (loading) {
          setLoading(false);
        }
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  const { run: handleInstallConfirm } = useRequest(deployAndStartADeployment, {
    onError: (e: any) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  const handelCheck = async () => {
    setLoading(true);
    try {
      await handlePreCheck({ name });
    } catch {
      setLoading(false);
    }
  };

  const { run: handleCreateConfig, loading: createLoading } = useRequest(
    createDeploymentConfig,
    {
      onSuccess: ({ success }: API.OBResponse) => {
        if (success) {
          handelCheck();
        }
        setLoading(false);
      },
      onError: (e: any) => {
        setCheckStatus(false);
        if (loading) {
          setLoading(false);
        }
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  const handleRetryCheck = (newConfigData?: any) => {
    setStatusData({});
    setFailedList([]);
    setShowFailedList([]);
    setCheckFinished(false);
    let params = { ...configData };
    if (newConfigData) {
      params = { ...newConfigData };
    }
    setLoading(true);
    handleCreateConfig({ name: oceanbase?.appname }, { ...params });
  };

  const { run: handleRecover, loading: recoverLoading } = useRequest(recover, {
    onSuccess: async ({
      success,
    }: API.OBResponseDataListRecoverChangeParameter_) => {
      if (success) {
        message.success(
          intl.formatMessage({
            id: 'OBD.pages.components.PreCheckStatus.AutomaticRepairSucceeded',
            defaultMessage: '自动修复成功',
          }),
        );
        try {
          const { success: nameSuccess, data: nameData } = await getInfoByName({
            name,
          });
          if (nameSuccess) {
            const { config } = nameData;
            setConfigData(config || {});
            handleRetryCheck(config);
          } else {
            message.error(
              intl.formatMessage({
                id: 'OBD.pages.components.PreCheckStatus.FailedToObtainConfigurationInformation',
                defaultMessage: '获取配置信息失败',
              }),
            );
          }
        } catch (e: any) {
          const errorInfo = getErrorInfo(e);
          setErrorVisible(true);
          setErrorsList([...errorsList, errorInfo]);
        }
      }
    },
    onError: (e: any) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  const handleStartCheck = () => {
    fetchPreCheckStatus({ name });
  };

  const prevStep = () => {
    setCheckOK(false);
    setCurrentStep(3);
    setCurrentPage(false);
    setErrorVisible(false);
    setErrorsList([]);
    window.scrollTo(0, 0);
  };

  const handleInstall = async () => {
    const { success } = await handleInstallConfirm({ name });
    if (success) {
      setCurrentStep(5);
      setCurrentPage(false);
      setErrorVisible(false);
      setErrorsList([]);
    }
  };

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

  const handleAutoRepair = () => {
    setHasAuto(false);
    handleRecover({ name });
  };

  useEffect(() => {
    if (onlyManual) {
      const newShowFailedList = failedList.filter((item) => !item.recoverable);
      setShowFailedList(newShowFailedList);
    } else {
      setShowFailedList(failedList);
    }
  }, [onlyManual]);

  useEffect(() => {
    handelCheck();
    const timelineContainer = document.getElementById('timeline-container');
    timelineContainer.onmousewheel = handleScrollTimeline; // ie , chrome
    timelineContainer?.addEventListener('DOMMouseScroll', handleScrollTimeline); // firefox
    return () => {
      timelineContainer.onmousewheel = () => {};
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
        failedContainer.onmousewheel = () => {};
        failedContainer?.removeEventListener(
          'DOMMouseScroll',
          handleScrollFailed,
        );
      }
    };
  }, [failedList]);

  let progressStatus = 'active';
  if (statusData?.status === 'FAILED') {
    progressStatus = 'exception';
  } else if (checkFinished) {
    if (statusData?.all_passed) {
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

  const checkItemLength = `${statusData?.finished || 0}/${
    statusData?.total || 0
  }`;
  const failedItemLength = failedList?.length;

  return (
    <Space className={styles.spaceWidth} direction="vertical" size="middle">
      <ProCard
        title={
          checkStatus
            ? checkFinished
              ? intl.formatMessage({
                  id: 'OBD.pages.components.PreCheckStatus.CheckCompleted',
                  defaultMessage: '检查完成',
                })
              : intl.formatMessage({
                  id: 'OBD.pages.components.PreCheckStatus.Checking',
                  defaultMessage: '检查中',
                })
            : intl.formatMessage({
                id: 'OBD.pages.components.PreCheckStatus.CheckFailed',
                defaultMessage: '检查失败',
              })
        }
        gutter={16}
        className="card-padding-bottom-24"
      >
        <ProCard
          title={intl.formatMessage(
            {
              id: 'OBD.pages.components.PreCheckStatus.CheckItemCheckitemlength',
              defaultMessage: '检查项 {checkItemLength}',
            },
            { checkItemLength: checkItemLength },
          )}
          colSpan={12}
          className={`${styles.preCheckSubCard} card-padding-bottom-24 `}
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
                id: 'OBD.pages.components.PreCheckStatus.PreCheckResultReCheck',
                defaultMessage: '预检查结果-重新检查',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.pages.components.PreCheckStatus.ReCheck',
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
                        NP.divide(statusData?.finished, statusData?.total),
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
                {statusData?.info?.map(
                  (item: API.PreCheckInfo, index: number) => (
                    <Timeline.Item
                      id={`${
                        (statusData?.info[index - 1]?.status === 'FINISHED' &&
                          item.status === 'PENDING') ||
                        (statusData?.all_passed &&
                          index === statusData?.info.length - 1)
                          ? 'running-timeline-item'
                          : ''
                      }`}
                      color={
                        statusColorConfig[
                          item.status === 'FINISHED' ? item.result : item.status
                        ]
                      }
                      dot={
                        item?.result ? (
                          item?.result === 'FAILED' ? (
                            <CloseCircleFilled style={{ fontSize: 10 }} />
                          ) : (
                            <CheckCircleFilled style={{ fontSize: 10 }} />
                          )
                        ) : null
                      }
                    >
                      {item?.name} {item?.server}
                    </Timeline.Item>
                  ),
                )}
              </Timeline>
            </>
          )}
        </ProCard>
        <ProCard
          title={intl.formatMessage(
            {
              id: 'OBD.pages.components.PreCheckStatus.FailedItemFaileditemlength',
              defaultMessage: '失败项 {failedItemLength}',
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
                    id: 'OBD.pages.components.PreCheckStatus.OnlyManualFixes',
                    defaultMessage: '只看手动修复项',
                  })}
                </Checkbox>
              ) : null}
              <Button
                className={styles.preCheckBtn}
                type="primary"
                disabled={!checkFinished || !hasAuto}
                onClick={handleAutoRepair}
                loading={recoverLoading}
                data-aspm-click="c307513.d317292"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.pages.components.PreCheckStatus.PreCheckResultAutomaticRepair',
                  defaultMessage: '预检查结果-自动修复',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.pages.components.PreCheckStatus.AutomaticRepair',
                  defaultMessage: '自动修复',
                })}
              </Button>
            </Space>
          }
        >
          {showFailedList?.length ? (
            <div className={styles.failedContainer} id="failed-container">
              {showFailedList?.map((item, index) => {
                let reason = '';
                if (item?.description) {
                  const index = item?.description.indexOf(':');
                  reason = item?.description.substring(
                    index,
                    item?.description.length,
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
                      title={item.description}
                      overlayClassName="list-tooltip"
                    >
                      <Text ellipsis>
                        <QuestionCircleFilled
                          className={`${styles.failedItemIcon} mr-10`}
                          style={{ color: '#8592ad', fontSize: '10px' }}
                        />
                        {intl.formatMessage({
                          id: 'OBD.pages.components.PreCheckStatus.Reason',
                          defaultMessage: '原因：',
                        })}
                        <a href={errCodeUrl} target="_blank">
                          OBD-{item.code}
                        </a>{' '}
                        {reason}
                      </Text>
                    </Tooltip>
                    <Tooltip
                      title={item.advisement?.description}
                      overlayClassName="list-tooltip"
                    >
                      <Text ellipsis>
                        <ReadFilled
                          className={`${styles.failedItemIcon} mr-10`}
                          style={{ color: '#8592ad', fontSize: '10px' }}
                        />
                        {intl.formatMessage({
                          id: 'OBD.pages.components.PreCheckStatus.Suggestions',
                          defaultMessage: '建议：',
                        })}
                        {item.recoverable ? (
                          <Tag className="green-tag">
                            {intl.formatMessage({
                              id: 'OBD.pages.components.PreCheckStatus.AutomaticRepair',
                              defaultMessage: '自动修复',
                            })}
                          </Tag>
                        ) : (
                          <Tag className="default-tag">
                            {intl.formatMessage({
                              id: 'OBD.pages.components.PreCheckStatus.ManualRepair',
                              defaultMessage: '手动修复',
                            })}
                          </Tag>
                        )}{' '}
                        {item.advisement?.description}
                      </Text>
                      <br />
                      <a
                        className={styles.preCheckLearnMore}
                        href={errCodeUrl}
                        target="_blank"
                      >
                        {intl.formatMessage({
                          id: 'OBD.pages.components.PreCheckStatus.LearnMore',
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
                    id: 'OBD.pages.components.PreCheckStatus.GreatNoFailedItems',
                    defaultMessage: '太棒了！无失败项',
                  })}
                </span>
              }
            />
          ) : (
            <div className={styles.preLoading}>
              {shape}
              <div className={styles.desc} style={{ color: '#8592ad' }}>
                {intl.formatMessage({
                  id: 'OBD.pages.components.PreCheckStatus.NoFailedItemsFoundYet',
                  defaultMessage: '暂未发现失败项',
                })}
              </div>
            </div>
          )}
        </ProCard>
      </ProCard>
      <footer className={styles.pageFooterContainer}>
        <div className={styles.pageFooter}>
          <Space className={styles.foolterAction}>
            <Button
              onClick={() => handleQuit(handleQuitProgress, setCurrentStep)}
              disabled={
                checkStatus &&
                (!checkFinished || recoverLoading || createLoading)
              }
              data-aspm-click="c307513.d317294"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.PreCheckStatus.PreCheckResultExit',
                defaultMessage: '预检查结果-退出',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.pages.components.PreCheckStatus.Exit',
                defaultMessage: '退出',
              })}
            </Button>
            <Button
              onClick={prevStep}
              disabled={checkStatus && !checkFinished}
              data-aspm-click="c307513.d317291"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.PreCheckStatus.PreCheckResultsPreviousStep',
                defaultMessage: '预检查结果-上一步',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.pages.components.PreCheckStatus.PreviousStep',
                defaultMessage: '上一步',
              })}
            </Button>
            {!statusData?.all_passed ? (
              <Tooltip
                title={intl.formatMessage({
                  id: 'OBD.pages.components.PreCheckStatus.FixAllFailedItems',
                  defaultMessage: '请修复全部失败项',
                })}
              >
                <Button
                  type="primary"
                  disabled={true}
                  data-aspm-click="c307510.d317287"
                  data-aspm-desc={intl.formatMessage({
                    id: 'OBD.pages.components.PreCheckStatus.PreCheckFailedDeploymentGreyed',
                    defaultMessage: '预检查失败-部署置灰',
                  })}
                  data-aspm-param={``}
                  data-aspm-expo
                >
                  {intl.formatMessage({
                    id: 'OBD.pages.components.PreCheckStatus.Deployment',
                    defaultMessage: '部署',
                  })}
                </Button>
              </Tooltip>
            ) : (
              <Button
                type="primary"
                onClick={handleInstall}
                data-aspm-click="c307503.d317272"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.pages.components.PreCheckStatus.PreCheckSuccessfulDeployment',
                  defaultMessage: '预检查成功-部署',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.pages.components.PreCheckStatus.Deployment',
                  defaultMessage: '部署',
                })}
              </Button>
            )}
          </Space>
        </div>
      </footer>
    </Space>
  );
}
