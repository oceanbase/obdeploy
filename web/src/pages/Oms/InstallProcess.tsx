import InstallProcessComp from '@/component/InstallProcessComp';
import {
  queryInstallLogOms,
  queryInstallStatusOms,
} from '@/services/ob-deploy-web/oms';
import { getErrorInfo } from '@/utils';
import { intl } from '@/utils/intl';
import useRequest, { requestPipeline } from '@/utils/useRequest';
import { Modal, notification } from 'antd';
import NP from 'number-precision';
import { useEffect, useRef, useState } from 'react';
import { history, useModel } from '@umijs/max';
import 'video.js/dist/video-js.css';
import * as OCP from '@/services/ocp_installer_backend/OCP';

let timerProgress: NodeJS.Timer;
const FINAL_UPGRADE_LOG_TIMEOUT = 5000;
const UPGRADE_POLLING_MODAL_THRESHOLD = 5;
type UpgradePollingChannel = 'status' | 'log';

const getUpgradePollingChannels = (
  channel?: UpgradePollingChannel,
): UpgradePollingChannel[] => (channel ? [channel] : ['status', 'log']);

export default function InstallProcess({
  type,
  taskId,
  onTaskFinished,
}: {
  type: 'install' | 'update';
  taskId?: number;
  onTaskFinished?: (taskId: number) => void;
}) {
  const {
    setCurrentStep,
    configData,
    setErrorVisible,
    setErrorsList,
    errorsList,
    omsConfigData,
  } = useModel('global');

  const {
    setInstallResult,
    installResult,
    installStatus,
    setInstallStatus,
    isReinstall,
    logData,
    setLogData,
    connectId,
    installTaskId: task_id
  } = useModel('ocpInstallData');

  const id = type === 'update' ? taskId : connectId;
  const name = type === "update" ? omsConfigData?.cluster_name : configData?.appname;
  const [progress, setProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(0);
  const [currentPage, setCurrentPage] = useState(true);
  const [statusData, setStatusData] = useState<API.TaskInfo>({});
  const [upgradeNotificationApi, upgradeNotificationContextHolder] =
    notification.useNotification();
  const [upgradeModalApi, upgradeModalContextHolder] = Modal.useModal();
  // update 模式专用的状态
  const [okCount, setOkCount] = useState(0); // 记录 "ok\n" 的数量
  const updateStartTimeRef = useRef<number | null>(null); // 记录开始时间
  const twoMinuteTimerRef = useRef<NodeJS.Timer | null>(null); // 两分钟定时器
  const taskPollTimerRef = useRef<NodeJS.Timer | null>(null);
  const taskLogPollTimerRef = useRef<NodeJS.Timer | null>(null);
  const finishTimerRef = useRef<NodeJS.Timer | null>(null);
  const activeUpgradeTaskIdRef = useRef<number>();
  const isPollingActiveRef = useRef(false);
  const finalLogAbortControllerRef = useRef<AbortController | null>(null);
  const upgradePollingFailuresRef = useRef<
    Record<UpgradePollingChannel, any[]>
  >({ status: [], log: [] });
  const upgradePollingModalRef = useRef<
    ReturnType<typeof upgradeModalApi.confirm> | null
  >(null);
  const upgradePollingModalChannelsRef = useRef<Set<UpgradePollingChannel>>(
    new Set(),
  );
  const upgradePollingModalShownRef = useRef(false);

  const isStaleUpgradeTask = () =>
    type === 'update' &&
    activeUpgradeTaskIdRef.current !== id;

  const clearUpgradePolling = () => {
    if (taskPollTimerRef.current) {
      clearTimeout(taskPollTimerRef.current);
      taskPollTimerRef.current = null;
    }
    if (taskLogPollTimerRef.current) {
      clearTimeout(taskLogPollTimerRef.current);
      taskLogPollTimerRef.current = null;
    }
  };

  const getUpgradePollingNotificationKey = (channel: UpgradePollingChannel) =>
    `oms-upgrade-${id ?? 'unknown'}-${channel}`;

  const clearUpgradePollingErrors = (channel?: UpgradePollingChannel) => {
    if (type !== 'update') {
      return;
    }
    const channels = getUpgradePollingChannels(channel);
    channels.forEach((currentChannel) => {
      upgradePollingFailuresRef.current[currentChannel] = [];
      upgradePollingModalChannelsRef.current.delete(currentChannel);
      upgradeNotificationApi.destroy(
        getUpgradePollingNotificationKey(currentChannel),
      );
    });
    if (upgradePollingModalChannelsRef.current.size === 0) {
      upgradePollingModalRef.current?.destroy();
      upgradePollingModalRef.current = null;
      upgradePollingModalShownRef.current = false;
    }
  };

  const openUpgradePollingModal = (
    channel: UpgradePollingChannel,
    errorInfo: API.ErrorInfo,
  ) => {
    upgradePollingModalChannelsRef.current.add(channel);
    if (upgradePollingModalShownRef.current) {
      return;
    }
    upgradePollingModalShownRef.current = true;
    let upgradeModal: ReturnType<typeof upgradeModalApi.confirm>;
    upgradeModal = upgradeModalApi.confirm({
      title: errorInfo.title,
      content: errorInfo.desc,
      okText: intl.formatMessage({
        id: 'OBD.pages.Layout.Exit',
        defaultMessage: '退出',
      }),
      cancelText: intl.formatMessage({
        id: 'OBD.pages.Layout.ContinueToWait',
        defaultMessage: '继续等待',
      }),
      afterClose: () => {
        if (upgradePollingModalRef.current === upgradeModal) {
          upgradePollingModalRef.current = null;
        }
      },
      onOk: () => {
        requestPipeline.processExit = true;
        history.push('/quit?path=update');
      },
    });
    upgradePollingModalRef.current = upgradeModal;
  };

  const recordPollingError = (
    error: any,
    channel: UpgradePollingChannel,
  ) => {
    if (type === 'update') {
      const channelFailures = upgradePollingFailuresRef.current[channel];
      if (error.code === 'ERR_NETWORK' || error.code === 'ERR_BAD_RESPONSE') {
        channelFailures.push(error);
        if (channelFailures.length < UPGRADE_POLLING_MODAL_THRESHOLD) {
          return;
        }
        const errorInfo = getErrorInfo({
          ...error,
          errorPipeline: channelFailures,
        });
        upgradeNotificationApi.destroy(
          getUpgradePollingNotificationKey(channel),
        );
        openUpgradePollingModal(channel, errorInfo);
      } else {
        clearUpgradePollingErrors(channel);
        const errorInfo = getErrorInfo(error);
        upgradeNotificationApi.error({
          key: getUpgradePollingNotificationKey(channel),
          description: errorInfo.desc,
          message: errorInfo.title,
          duration: null,
        });
      }
      return;
    }
    setInstallResult('FAILED');
    const errorInfo = getErrorInfo(error);
    setErrorVisible(true);
    setErrorsList((currentErrors) => [...currentErrors, errorInfo]);
  };

  const getInstallTaskFn = type === "update" ? OCP.getOmsUpgradeTask : OCP.getOmsInstallTask
  const getInstallTaskLogFn = type === "update" ? OCP.getOmsUpgradeTaskLog : OCP.getOmsInstallTaskLog
  const getReinstallTaskFn = OCP.getOmsReinstallTask;
  const getreInstallTaskLogFn = OCP.getOmsReinstallTaskLog;
  const getTaskFn = isReinstall ? getReinstallTaskFn : getInstallTaskFn;
  const getTaskLogFn = isReinstall
    ? getreInstallTaskLogFn
    : getInstallTaskLogFn;

  const finishUpgradeTask = async (data: API.TaskInfo) => {
    finalLogAbortControllerRef.current?.abort();
    const controller = new AbortController();
    finalLogAbortControllerRef.current = controller;
    const finalLogTimeout = window.setTimeout(
      () => controller.abort(),
      FINAL_UPGRADE_LOG_TIMEOUT,
    );
    try {
      const logResponse = await OCP.getOmsUpgradeTaskLog({
        cluster_name: name,
        task_id: id,
      }, {
        signal: controller.signal,
      });
      if (isStaleUpgradeTask()) {
        return;
      }
      if (logResponse?.success) {
        setLogData(logResponse.data || {});
      }
    } catch {
      // The task result is authoritative; retain the latest polled log if the final log query fails.
    } finally {
      window.clearTimeout(finalLogTimeout);
      if (finalLogAbortControllerRef.current === controller) {
        finalLogAbortControllerRef.current = null;
      }
    }

    if (isStaleUpgradeTask()) {
      return;
    }
    clearUpgradePollingErrors();
    setInstallStatus(data?.status);
    setInstallResult(data?.result);
    setCurrentPage(false);
    if (id !== undefined) {
      onTaskFinished?.(id);
    }
  };


  const { run: fetchInstallStatus } = useRequest(queryInstallStatusOms, {
    onSuccess: ({ success, data }: API.OBResponseTaskInfo_) => {
      if (success) {
        setStatusData(data || {});
        clearInterval(timerProgress);
        // update 模式下不使用 fetchInstallStatus 更新状态，由 getInstallTask 负责
        if (type !== "update") {
          if (data?.status !== 'RUNNING') {
            setInstallStatus(data?.status);
            setCurrentPage(false);
            setTimeout(() => {
              setCurrentStep(6);
              setErrorVisible(false);
              setErrorsList([]);
            }, 2000);
          } else {
            setTimeout(() => {
              fetchInstallStatus({ name });
            }, 1000);
          }
        }
        const newProgress = NP.divide(data?.finished, data?.total).toFixed(2);
        setProgress(newProgress);
        let step = NP.minus(newProgress, progress);
        let stepNum = 1;
        timerProgress = setInterval(() => {
          const currentProgressNumber = NP.plus(
            progress,
            NP.times(NP.divide(step, 100), stepNum),
          );

          if (currentProgressNumber >= 1) {
            clearInterval(timerProgress);
          } else {
            stepNum += 1;
            setShowProgress(currentProgressNumber);
          }
        }, 10);
      }
    },
    onError: (e: any) => {
      if (currentPage && !requestPipeline.processExit) {
        setTimeout(() => {
          fetchInstallStatus({ name });
        }, 1000);
      }
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  const { run: handleInstallLog } = useRequest(queryInstallLogOms, {
    onSuccess: ({ success, data }: API.OBResponseInstallLog_) => {
      if (success && installStatus === 'RUNNING') {
        setLogData(data || {});
        setTimeout(() => {
          handleInstallLog({ name });
        }, 1000);
      }
    },
    onError: (e: any) => {
      if (
        installStatus === 'RUNNING' &&
        currentPage &&
        !requestPipeline.processExit
      ) {
        setTimeout(() => {
          handleInstallLog({ name });
        }, 1000);
      }
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  const { run: getInstallTask, cancel: cancelGetInstallTask } = useRequest(getTaskFn, {
    manual: true,
    skipRequestPipeline: type === 'update',
    onSuccess: ({ success, data }) => {
      if (isStaleUpgradeTask()) {
        return;
      }
      if (success) {
        clearUpgradePollingErrors('status');
        setStatusData(data || {});
        clearInterval(timerProgress);
        setInstallResult(data?.result);

        // update 模式下的特殊逻辑：当 result === "SUCCESSFUL" 或 "successful" 时，设置进度为 100%
        if (type === "update" && (data?.result === "SUCCESSFUL" || data?.result === "successful")) {
          setShowProgress(1); // 100%
          // 清除两分钟定时器
          if (twoMinuteTimerRef.current) {
            clearTimeout(twoMinuteTimerRef.current);
            twoMinuteTimerRef.current = null;
          }
        }

        // 更新状态：如果 status 存在且不是 RUNNING，则更新
        if (data?.status && data?.status !== 'RUNNING') {
          if (type === 'update') {
            isPollingActiveRef.current = false;
            clearUpgradePolling();
            cancelGetInstallTaskLog();
            void finishUpgradeTask(data);
          } else {
            setInstallStatus(data?.status);
            setInstallResult(data?.result);
            setCurrentPage(false);
            finishTimerRef.current = setTimeout(() => {
              setCurrentStep(6);
              setErrorVisible(false);
              setErrorsList([]);
            }, 2000);
          }
        } else if (data?.status === 'RUNNING') {
          // 如果状态是 RUNNING，继续轮询
          taskPollTimerRef.current = setTimeout(() => {
            if (isStaleUpgradeTask()) {
              return;
            }
            if (type === "update") {
              getInstallTask({ cluster_name: name, task_id: id });
            } else {
              getInstallTask({ id, task_id });
            }
          }, 2000);
        }

        // 原有的进度逻辑（只在 install 模式下使用）
        if (type !== "update") {
          const finished = data?.info?.filter(
            (item) => item.status === 'FINISHED' && item.result === 'SUCCESSFUL',
          ).length;
          const newProgress = Number(
            NP.divide(finished, data?.info?.length).toFixed(2),
          );
          setProgress(newProgress);
          let step = NP.minus(newProgress, progress);
          let stepNum = 1;
          timerProgress = setInterval(() => {
            const currentProgressNumber = NP.plus(
              progress,
              NP.times(NP.divide(step, 100), stepNum),
            );

            if (currentProgressNumber >= 1) {
              clearInterval(timerProgress);
            } else {
              stepNum += 1;
              setShowProgress(currentProgressNumber);
            }
          }, 10);
        }
      }
    },
    onError: (e: any) => {
      if (isStaleUpgradeTask()) {
        return;
      }
      if (type === 'update' && !isPollingActiveRef.current) {
        return;
      }
      if (currentPage && !requestPipeline.processExit) {
        taskPollTimerRef.current = setTimeout(() => {
          if (isStaleUpgradeTask()) {
            return;
          }
          if (type === "update") {
            getInstallTask({ cluster_name: name, task_id: id });
          } else {
            getInstallTask({ id, task_id });
          }
        }, 2000);
      }
      recordPollingError(e, 'status');
    },
  });
  const { run: getInstallTaskLog, cancel: cancelGetInstallTaskLog } = useRequest(getTaskLogFn, {
    manual: true,
    skipRequestPipeline: type === 'update',
    onSuccess: ({ success, data }: API.OBResponseInstallLog_) => {
      if (isStaleUpgradeTask()) {
        return;
      }
      if (type === 'update' && !isPollingActiveRef.current) {
        return;
      }
      if (success) {
        clearUpgradePollingErrors('log');
        setLogData(data || {});

        // update 模式下的特殊进度逻辑
        if (type === "update") {
          // 记录开始时间（第一次调用时）
          if (updateStartTimeRef.current === null) {
            updateStartTimeRef.current = Date.now();
          }

          // 统计 "ok\n" 的数量
          const logContent = data?.log || '';
          const okMatches = logContent.match(/ok\n/g);
          const currentOkCount = okMatches ? okMatches.length : 0;

          // 如果 ok 数量增加了，更新进度
          if (currentOkCount > okCount) {
            setOkCount(currentOkCount);

            // 根据 ok 数量计算目标进度
            let targetProgress = 0;
            if (currentOkCount >= 5) {
              targetProgress = 0.50; // 50%
            } else if (currentOkCount >= 2) {
              targetProgress = 0.10; // 10%
            } else if (currentOkCount >= 1) {
              targetProgress = 0.05; // 5%
            }

            // 使用函数式更新，确保进度只增不减
            setShowProgress((prev) => {
              return Math.max(prev, targetProgress);
            });
          }
        }
      }

      if (
        success &&
        installStatus === 'RUNNING' &&
        (type !== 'update' || isPollingActiveRef.current)
      ) {
        taskLogPollTimerRef.current = setTimeout(() => {
          if (isStaleUpgradeTask()) {
            return;
          }
          if (type === "update") {
            getInstallTaskLog({ cluster_name: name, task_id: id });
          } else {
            getInstallTaskLog({ id, task_id });
          }
        }, 2000);
      }
    },
    onError: (e: any) => {
      if (isStaleUpgradeTask()) {
        return;
      }
      if (type === 'update' && !isPollingActiveRef.current) {
        return;
      }
      if (
        installStatus === 'RUNNING' &&
        currentPage &&
        !requestPipeline.processExit
      ) {
        taskLogPollTimerRef.current = setTimeout(() => {
          if (isStaleUpgradeTask()) {
            return;
          }
          if (type === "update") {
            getInstallTaskLog({ cluster_name: name, task_id: id });
          } else {
            getInstallTaskLog({ id, task_id });
          }
        }, 2000);
      }
      recordPollingError(e, 'log');
    },
  });
  useEffect(() => {
    if (type === "install" && id && task_id) {
      setInstallResult('RUNNING');
      setInstallStatus('RUNNING');
      getInstallTask({ id, task_id });
      getInstallTaskLog({ id, task_id });
    }
  }, [name, id, task_id]);

  useEffect(() => {
    if (type === "update" && name && id) {
      finalLogAbortControllerRef.current?.abort();
      finalLogAbortControllerRef.current = null;
      activeUpgradeTaskIdRef.current = id;
      isPollingActiveRef.current = true;
      upgradePollingFailuresRef.current = { status: [], log: [] };
      upgradePollingModalChannelsRef.current.clear();
      upgradePollingModalShownRef.current = false;
      clearUpgradePolling();
      setInstallResult('RUNNING');
      setInstallStatus('RUNNING');
      // 重置 update 模式的状态
      setOkCount(0);
      setShowProgress(0);
      updateStartTimeRef.current = Date.now();

      // 启动两分钟定时器
      if (twoMinuteTimerRef.current) {
        clearTimeout(twoMinuteTimerRef.current);
      }
      twoMinuteTimerRef.current = setTimeout(() => {
        // 两分钟后，如果进度小于 70%，设置为 70%
        setShowProgress((prev) => {
          if (prev < 0.70) {
            return 0.70;
          }
          return prev;
        });
      }, 2 * 60 * 1000); // 2分钟

      getInstallTask({ cluster_name: name, task_id: id });
      getInstallTaskLog({ cluster_name: name, task_id: id });
    }

    // 清理函数
    return () => {
      isPollingActiveRef.current = false;
      clearUpgradePollingErrors();
      activeUpgradeTaskIdRef.current = undefined;
      clearUpgradePolling();
      cancelGetInstallTask();
      cancelGetInstallTaskLog();
      finalLogAbortControllerRef.current?.abort();
      finalLogAbortControllerRef.current = null;
      clearInterval(timerProgress);
      if (twoMinuteTimerRef.current) {
        clearTimeout(twoMinuteTimerRef.current);
        twoMinuteTimerRef.current = null;
      }
      if (finishTimerRef.current) {
        clearTimeout(finishTimerRef.current);
        finishTimerRef.current = null;
      }
    };
  }, [omsConfigData?.cluster_name, id, type, getInstallTask, getInstallTaskLog]);

  return (
    <>
      {upgradeNotificationContextHolder}
      {upgradeModalContextHolder}
      <InstallProcessComp
        logData={logData}
        installStatus={installStatus}
        installResult={installResult}
        statusData={statusData}
        showProgress={showProgress}
        type={type}
      />
    </>
  );
}
