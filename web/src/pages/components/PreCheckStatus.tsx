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
  installDeployment,
  createDeploymentConfig,
  recover,
} from '@/services/ob-deploy-web/Deployments';
import { handleQuit, handleResponseError } from '@/utils';
import NP from 'number-precision';
import styles from './index.less';

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
  const [lastError, setLastError] = useState('');
  const [currentPage, setCurrentPage] = useState(true);
  const [firstErrorTimestamp, setFirstErrorTimestamp] = useState<number>();

  const { run: fetchPreCheckStatus } = useRequest(preCheckStatus, {
    skipStatusError: true,
    skipTypeError: true,
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
          handleResponseError(data?.message);
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
        const errorInfo =
          data?.msg ||
          data?.detail ||
          response?.statusText ||
          '您的网络发生异常，无法连接服务器';
        const errorInfoStr = errorInfo ? JSON.stringify(errorInfo) : '';
        if (errorInfoStr && lastError !== errorInfoStr) {
          setLastError(errorInfoStr);
          handleResponseError(errorInfo);
        }
      };
      if (response?.status === 504 || (!response && type === 'TypeError')) {
        const nowTime = new Date().getTime();
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
      onError: () => {
        setCheckStatus(false);
        if (loading) {
          setLoading(false);
        }
      },
    },
  );

  const { run: handleInstallConfirm } = useRequest(installDeployment);

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
      onError: () => {
        setCheckStatus(false);
        if (loading) {
          setLoading(false);
        }
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
        message.success('自动修复成功');
        try {
          const { success: nameSuccess, data: nameData } = await getInfoByName({
            name,
          });
          if (nameSuccess) {
            const { config } = nameData;
            setConfigData(config || {});
            handleRetryCheck(config);
          } else {
            message.error('获取配置信息失败');
          }
        } catch (e: any) {
          const { response, data } = e;
          handleResponseError(
            data?.msg || data?.detail || response?.statusText,
          );
        }
      }
    },
  });

  const handleStartCheck = () => {
    fetchPreCheckStatus({ name });
  };

  const prevStep = () => {
    setCheckOK(false);
    setCurrentStep(3);
    setCurrentPage(false);
  };

  const handleInstall = async () => {
    const { success } = await handleInstallConfirm({ name });
    if (success) {
      setCurrentStep(5);
      setCurrentPage(false);
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
          ); // firefox
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

  return (
    <Space className={styles.spaceWidth} direction="vertical" size="middle">
      <ProCard
        title={
          checkStatus ? (checkFinished ? '检查完成' : '检查中') : '检查失败'
        }
        gutter={16}
        className="card-padding-bottom-24"
      >
        <ProCard
          title={`检查项 ${statusData?.finished || 0}/${
            statusData?.total || 0
          }`}
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
              data-aspm-desc="预检查结果-重新检查"
              data-aspm-param={``}
              data-aspm-expo
            >
              重新检查
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
          title={`失败项 ${failedList?.length}`}
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
                  只看手动修复项
                </Checkbox>
              ) : null}
              <Button
                className={styles.preCheckBtn}
                type="primary"
                disabled={!checkFinished || !hasAuto}
                onClick={handleAutoRepair}
                loading={recoverLoading}
                data-aspm-click="c307513.d317292"
                data-aspm-desc="预检查结果-自动修复"
                data-aspm-param={``}
                data-aspm-expo
              >
                自动修复
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
                    <Text>
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
                        原因：
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
                        建议：
                        {item.recoverable ? (
                          <Tag className="green-tag">自动修复</Tag>
                        ) : (
                          <Tag className="default-tag">手动修复</Tag>
                        )}{' '}
                        {item.advisement?.description}
                      </Text>
                      <br />
                      <a
                        href={errCodeUrl}
                        target="_blank"
                        style={{
                          display: 'inline-block',
                          marginLeft: 60,
                          marginTop: '6px',
                        }}
                      >
                        了解更多方案
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
                <span style={{ color: '#8592ad' }}>太棒了！无失败项</span>
              }
            />
          ) : (
            <div className={styles.preLoading}>
              {shape}
              <div className={styles.desc} style={{ color: '#8592ad' }}>
                暂未发现失败项
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
              data-aspm-desc="预检查结果-退出"
              data-aspm-param={``}
              data-aspm-expo
            >
              退出
            </Button>
            <Button
              onClick={prevStep}
              disabled={checkStatus && !checkFinished}
              data-aspm-click="c307513.d317291"
              data-aspm-desc="预检查结果-上一步"
              data-aspm-param={``}
              data-aspm-expo
            >
              上一步
            </Button>
            {!statusData?.all_passed ? (
              <Tooltip title="请修复全部失败项">
                <Button
                  type="primary"
                  disabled={true}
                  data-aspm-click="c307510.d317287"
                  data-aspm-desc="预检查失败-部署置灰"
                  data-aspm-param={``}
                  data-aspm-expo
                >
                  部署
                </Button>
              </Tooltip>
            ) : (
              <Button
                type="primary"
                onClick={handleInstall}
                data-aspm-click="c307503.d317272"
                data-aspm-desc="预检查成功-部署"
                data-aspm-param={``}
                data-aspm-expo
              >
                部署
              </Button>
            )}
          </Space>
        </div>
      </footer>
    </Space>
  );
}
