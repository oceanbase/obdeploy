import InstallProcessComp from '@/component/InstallProcessComp';
import {
  queryInstallLogOms,
  queryInstallStatusOms,
} from '@/services/ob-deploy-web/Deployments';
import { getErrorInfo } from '@/utils';
import useRequest, { requestPipeline } from '@/utils/useRequest';
import NP from 'number-precision';
import { useEffect, useState } from 'react';
import { useModel } from 'umi';
import 'video.js/dist/video-js.css';
import * as OCP from '@/services/ocp_installer_backend/OCP';

let timerProgress: NodeJS.Timer;
export default function InstallProcess() {
  const {
    setCurrentStep,
    configData,
    installStatus,
    setInstallStatus,
    setErrorVisible,
    setErrorsList,
    errorsList,
  } = useModel('global');

  const {
    setInstallResult,
    isReinstall,
    logData,
    setLogData,
    connectId: id,
    installTaskId: task_id
  } = useModel('ocpInstallData');

  const name = configData?.appname;
  const [progress, setProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(0);
  const [currentPage, setCurrentPage] = useState(true);
  const [statusData, setStatusData] = useState<API.TaskInfo>({});

  const getInstallTaskFn = OCP.getOmsInstallTask
  const getInstallTaskLogFn = OCP.getOmsInstallTaskLog
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
        if (data?.status && data?.status !== 'RUNNING') {
          setInstallStatus(data?.status);
          setCurrentPage(false);
          setTimeout(() => {
            setCurrentStep(6);
            setErrorVisible(false);
            setErrorsList([]);
          }, 2000);
        } else {
          setTimeout(() => {
            getInstallTask({ id, task_id });
          }, 2000);
        }
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
    },
    onError: (e: any) => {
      if (currentPage && !requestPipeline.processExit) {
        setTimeout(() => {
          getInstallTask({ id, task_id });
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
      if (success) setLogData(data || {});
      if (success && installStatus === 'RUNNING') {
        setTimeout(() => {
          getInstallTaskLog({ id, task_id });
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
          getInstallTaskLog({ id, task_id });
        }, 2000);
      }
      setInstallResult('FAILED');
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });
  useEffect(() => {
    if (id && task_id) {
      setInstallResult('RUNNING');
      setInstallStatus('RUNNING');
      getInstallTask({ id, task_id });
      getInstallTaskLog({ id, task_id });
    }
  }, [name, id, task_id]);

  return (
    <InstallProcessComp
      logData={logData}
      installStatus={installStatus}
      statusData={statusData}
      showProgress={showProgress}
      type="OMS"
    />
  );
}
