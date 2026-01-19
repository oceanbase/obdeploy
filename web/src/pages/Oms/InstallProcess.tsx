import InstallProcessComp from '@/component/InstallProcessComp';
import {
  queryInstallLogOms,
  queryInstallStatusOms,
} from '@/services/ob-deploy-web/Deployments';
import { getErrorInfo } from '@/utils';
import useRequest, { requestPipeline } from '@/utils/useRequest';
import NP from 'number-precision';
import { useEffect, useRef, useState } from 'react';
import { useModel } from 'umi';
import 'video.js/dist/video-js.css';
import * as OCP from '@/services/ocp_installer_backend/OCP';

let timerProgress: NodeJS.Timer;
export default function InstallProcess({
  type,
}: {
  type: 'install' | 'update';
}) {
  const {
    setCurrentStep,
    configData,
    setErrorVisible,
    setErrorsList,
    errorsList,
    ocpConfigData,
  } = useModel('global');

  const {
    setInstallResult,
    installResult,
    installStatus,
    setInstallStatus,
    isReinstall,
    logData,
    setLogData,
    connectId: id,
    installTaskId: task_id
  } = useModel('ocpInstallData');

  const name = type === "update" ? ocpConfigData?.cluster_name : configData?.appname;
  const [progress, setProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(0);
  const [currentPage, setCurrentPage] = useState(true);
  const [statusData, setStatusData] = useState<API.TaskInfo>({});
  // update 模式专用的状态
  const [okCount, setOkCount] = useState(0); // 记录 "ok\n" 的数量
  const updateStartTimeRef = useRef<number | null>(null); // 记录开始时间
  const twoMinuteTimerRef = useRef<NodeJS.Timer | null>(null); // 两分钟定时器

  const getInstallTaskFn = type === "update" ? OCP.getOmsUpgradeTask : OCP.getOmsInstallTask
  const getInstallTaskLogFn = type === "update" ? OCP.getOmsUpgradeTaskLog : OCP.getOmsInstallTaskLog
  const getReinstallTaskFn = OCP.getOmsReinstallTask;
  const getreInstallTaskLogFn = OCP.getOmsReinstallTaskLog;
  const getTaskFn = isReinstall ? getReinstallTaskFn : getInstallTaskFn;
  const getTaskLogFn = isReinstall
    ? getreInstallTaskLogFn
    : getInstallTaskLogFn;


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

  const { run: getInstallTask } = useRequest(getTaskFn, {
    manual: true,
    onSuccess: ({ success, data }) => {
      if (success) {
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
          setInstallStatus(data?.status);
          setInstallResult(data?.result);
          setCurrentPage(false);
          setTimeout(() => {
            if (type === "install") {
              setCurrentStep(6);
            }
            setErrorVisible(false);
            setErrorsList([]);
          }, 2000);
        } else if (data?.status === 'RUNNING') {
          // 如果状态是 RUNNING，继续轮询
          setTimeout(() => {
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
      if (currentPage && !requestPipeline.processExit) {
        setTimeout(() => {
          if (type === "update") {
            getInstallTask({ cluster_name: name, task_id: id });
          } else {
            getInstallTask({ id, task_id });
          }
        }, 2000);
      }
      setInstallResult('FAILED');
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });
  const { run: getInstallTaskLog } = useRequest(getTaskLogFn, {
    manual: true,
    onSuccess: ({ success, data }: API.OBResponseInstallLog_) => {
      if (success) {
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

      if (success && installStatus === 'RUNNING') {
        setTimeout(() => {
          if (type === "update") {
            getInstallTaskLog({ cluster_name: name, task_id: id });
          } else {
            getInstallTaskLog({ id, task_id });
          }
        }, 2000);
      }
    },
    onError: (e: any) => {
      if (
        installStatus === 'RUNNING' &&
        currentPage &&
        !requestPipeline.processExit
      ) {
        setTimeout(() => {
          if (type === "update") {
            getInstallTaskLog({ cluster_name: name, task_id: id });
          } else {
            getInstallTaskLog({ id, task_id });
          }
        }, 2000);
      }
      setInstallResult('FAILED');
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
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
      if (twoMinuteTimerRef.current) {
        clearTimeout(twoMinuteTimerRef.current);
        twoMinuteTimerRef.current = null;
      }
    };
  }, [ocpConfigData?.cluster_name, id, type, getInstallTask, getInstallTaskLog]);

  return (
    <InstallProcessComp
      logData={logData}
      installStatus={installStatus}
      installResult={installResult}
      statusData={statusData}
      showProgress={showProgress}
      type={type}
    />
  );
}
