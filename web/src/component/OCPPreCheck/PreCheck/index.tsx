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
import * as OCP from '@/services/ocp_installer_backend/OCP';
import customRequest from '@/utils/useRequest';
import { useRequest } from 'ahooks';
import {
  deployAndStartADeployment,
  createDeploymentConfig,
} from '@/services/ob-deploy-web/Deployments';
import { getErrorInfo, errorHandler } from '@/utils';
import CustomFooter from '../../CustomFooter';
import ExitBtn from '@/component/ExitBtn';
import NP from 'number-precision';
import { getLocale } from 'umi';
import ZhStyles from '@/pages/Obdeploy/indexZh.less';
import EnStyles from '@/pages/Obdeploy/indexEn.less';

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
interface PreCheckProps {
  isNewDB: boolean;
}

// result: RUNNING | FALIED | SUCCESSFUL
// status: RUNNING | FINISHED
export default function PreCheck({
  current,
  setCurrent,
}: PreCheckProps & API.StepProp) {
  const {
    setCheckOK,
    setErrorVisible,
    setErrorsList,
    errorsList,
    ocpConfigData,
    ERR_CODE
  } = useModel('global');
  const { setInstallTaskId } = useModel('ocpInstallData');

  const { connectId } = useModel('ocpInstallData');
  const oceanbase = ocpConfigData?.components?.oceanbase;
  const name = ocpConfigData?.components?.oceanbase?.appname;
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
  const {
    data: precheckOcpDatas,
    run: precheckOcp,
    refresh,
    loading: ocpPrecheckLoading,
  } = useRequest(OCP.precheckOcp, {
    manual: true,
    onSuccess: (res: any) => {
      if (res?.success) {
        const { data } = res;
        let timer: NodeJS.Timer;
        data.finished =
          data?.task_info?.info.filter(
            (item) => item.result === 'SUCCESSFUL' || item.result === 'FAILED',
          ).length || 0;
        data.total = data?.precheck_result?.length || 0;
        data.all_passed = data.task_info.result === 'SUCCESSFUL';
        setStatusData(data || {});
        if (data?.task_info?.status === 'RUNNING') {
          timer = setTimeout(() => {
            refresh();
          }, 2000);
        }
        if (
          data?.task_info?.result === 'FAILED' &&
          data?.precheck_result.find((item: any) => item.result === 'RUNNING')
        ) {
          const newFailedList =
            data?.precheck_result?.filter(
              (item: any) => item.result === 'FAILED',
            ) || [];
          setShowFailedList(newFailedList);
          setFailedList(newFailedList);
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
          setCheckFinished(true);
        } else {
          if (data.all_passed) {
            setFailedList([]);
            setShowFailedList([]);
          } else {
            const newFailedList =
              data?.precheck_result?.filter(
                (item: any) => item.result === 'FAILED',
              ) || [];
            newFailedList.forEach((item: any) => {
              if (item.recoverable) {
                setHasAuto(true);
              } else {
                setHasManual(true);
              }
            });
            setFailedList(newFailedList);
            setShowFailedList(newFailedList);
          }
          // const isFinished = !!data?.total && data?.finished === data?.total;
          const isFinished = data.task_info.status === 'FINISHED';
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
              if (timelineContainer) {
                timelineContainer.scrollTop = NP.minus(
                  NP.strip(runningItemDom?.offsetTop),
                  150,
                );
              }
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
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  // 发起OCP的预检查
  const {
    run: precheckOcpDeployment,
    refresh: rePrecheckOcpDeployment,
    loading: preCheckLoading,
  } = useRequest(OCP.precheckOcpDeployment, {
    manual: true,
    onSuccess: (res: any) => {
      if (res.success) {
        precheckOcp({
          id: connectId,
          task_id: res.data?.id,
        });
      }
    },
    onError: ({ response, data }: any) => {
      errorHandler({ response, data });
    },
  });

  const { run: handleInstallConfirm } = customRequest(
    deployAndStartADeployment,
    {
      onError: (e: any) => {
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  const handelCheck = async () => {
    setLoading(true);
    try {
      if (connectId) {
        await precheckOcpDeployment({ id: connectId });
      }
    } catch {
      setLoading(false);
    }
  };

  const { run: handleCreateConfig, loading: createLoading } = useRequest(
    createDeploymentConfig,
    {
      manual: true,
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
    let params = { ...ocpConfigData };
    if (newConfigData) {
      params = { ...newConfigData };
    }
    precheckOcpDeployment({ id: connectId });
  };

  const { run: handleRecover, loading: recoverLoading } = useRequest(
    OCP.recoverOcpDeployment,
    {
      manual: true,
      onSuccess: async ({ success }) => {
        if (success) {
          message.success(
            intl.formatMessage({
              id: 'OBD.OCPPreCheck.PreCheck.AutomaticRepairSucceeded',
              defaultMessage: '自动修复成功',
            }),
          );
          try {
            rePrecheckOcpDeployment();
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
    },
  );

  const prevStep = () => {
    setCheckOK(false);
    setCurrent(current - 1);
    setCurrentPage(false);
    setErrorVisible(false);
    setErrorsList([]);
    window.scrollTo(0, 0);
  };

  const { run: installOcp, loading: precheckLoading } = useRequest(
    OCP.installOcp,
    {
      manual: true,
      onSuccess: ({ data, success }) => {
        if (success) {
          setInstallTaskId(data?.id);
          setCurrent(5);
          setCurrent(current + 1);
          setCurrentPage(false);
          setErrorVisible(false);
          setErrorsList([]);
        }
      },
      onError: (e: any) => {
        const errorInfo = getErrorInfo(e);
        setErrorVisible(true);
        setErrorsList([...errorsList, errorInfo]);
      },
    },
  );

  const handleInstall = async () => {
    installOcp({
      id: connectId,
    });
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
    handleRecover({ id: connectId });
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
    precheckOcpDeployment({ id: connectId });
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
          className={`${styles.preCheckSubCard}  card-padding-bottom-24 `}
          bodyStyle={{ paddingRight: 0, overflow: 'hidden' }}
          extra={
            <Button
              className={styles.preCheckBtn}
              disabled={
                checkStatus &&
                (!checkFinished || createLoading || preCheckLoading)
                //   ||
                // statusData.all_passed
              }
              onClick={() => handleRetryCheck()}
              data-aspm-click="ca54438.da43444"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.OCPPreCheck.PreCheck.PreCheckResultReCheck',
                defaultMessage: '预检查结果-重新检查',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              {intl.formatMessage({
                id: 'OBD.OCPPreCheck.PreCheck.ReCheck',
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
                {statusData?.precheck_result?.map(
                  (item: API.PreCheckInfo, index: number) => {
                    //根据索引找到对应项
                    const task_info_item =
                      statusData?.task_info?.info[index - 1];
                    return (
                      <Timeline.Item
                        // id={`${
                        //   (statusData?.info[index - 1]?.status === 'FINISHED' &&
                        //     item.status === 'PENDING') ||
                        //   (statusData?.all_passed &&
                        //     index === statusData?.info.length - 1)
                        //     ? 'running-timeline-item'
                        //     : ''
                        // }`}
                        key={index}
                        id={`${
                          task_info_item?.result === 'RUNNING'
                            ? 'running-timeline-item'
                            : ''
                        }`}
                        // color={
                        //   statusColorConfig[
                        //     item.status === 'FINISHED' ? item.result : item.status
                        //   ]
                        // }
                        color={statusColorConfig[task_info_item?.result]}
                        dot={
                          task_info_item?.result ? (
                            task_info_item?.result === 'FAILED' ? (
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
                data-aspm-click="ca54438.da43445"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.OCPPreCheck.PreCheck.PreCheckResultAutomaticRepair',
                  defaultMessage: '预检查结果-自动修复',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                {intl.formatMessage({
                  id: 'OBD.OCPPreCheck.PreCheck.AutomaticRepair',
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
                if (item?.advisement) {
                  const index = item?.advisement.indexOf(':');
                  reason = item?.advisement.substring(
                    index,
                    item?.advisement.length,
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
                      title={item.advisement}
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
                        <a href={ERR_CODE} target="_blank">
                          ERR-{item.code}
                        </a>{' '}
                        {reason}
                      </Text>
                    </Tooltip>
                    <Tooltip
                      title={item.advisement}
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
                        {item.advisement}
                      </Text>
                      <br />
                      <a
                        className={styles.preCheckLearnMore}
                        href={ERR_CODE}
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
      <CustomFooter>
        {' '}
        <ExitBtn />
        <Button
          data-aspm-click="ca54438.da43446"
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.OCPPreCheck.PreCheck.PreCheckResultsPreviousStep',
            defaultMessage: '预检查结果-上一步',
          })}
          data-aspm-param={``}
          data-aspm-expo
          onClick={prevStep}
          disabled={checkStatus && !checkFinished}
        >
          {intl.formatMessage({
            id: 'OBD.OCPPreCheck.PreCheck.PreviousStep',
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
              data-aspm-click="ca54439.da43447"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.OCPPreCheck.PreCheck.PreCheckFailedDeploymentGreyed',
                defaultMessage: '预检查失败-部署置灰',
              })}
              data-aspm-param={``}
              data-aspm-expo
              type="primary"
              disabled={true}
            >
              {intl.formatMessage({
                id: 'OBD.OCPPreCheck.PreCheck.NextStep',
                defaultMessage: '下一步',
              })}
            </Button>
          </Tooltip>
        ) : (
          <Button
            data-aspm-click="ca54440.da43441"
            data-aspm-desc={intl.formatMessage({
              id: 'OBD.OCPPreCheck.PreCheck.PreCheckSuccessfulDeployment',
              defaultMessage: '预检查成功-部署',
            })}
            data-aspm-param={``}
            data-aspm-expo
            type="primary"
            loading={precheckLoading}
            onClick={handleInstall}
          >
            {intl.formatMessage({
              id: 'OBD.OCPPreCheck.PreCheck.NextStep',
              defaultMessage: '下一步',
            })}
          </Button>
        )}
      </CustomFooter>
    </Space>
  );
}
