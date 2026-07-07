import InstallProcessComp from '@/component/InstallProcessComp';
import {
  queryInstallLog,
  queryInstallStatus,
} from '@/services/ob-deploy-web/Deployments';
import { getErrorInfo } from '@/utils';
import useRequest, { requestPipeline } from '@/utils/useRequest';
import NP from 'number-precision';
import { useEffect, useRef, useState } from 'react';
import { useModel } from '@umijs/max';
import { prefetchConnectionInfo } from './InstallFinished';
import 'video.js/dist/video-js.css';

const preloadResultImage = (status?: string) =>
  new Promise<void>((resolve) => {
    const img = new Image();
    img.onload = img.onerror = () => resolve();
    img.src =
      status === 'SUCCESSFUL'
        ? '/assets/successful.png'
        : '/assets/failed.png';
  });

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
    setPrefetchedConnectInfo,
    deployMode,
  } = useModel('global');
  const seekdb = deployMode === 'seekdb';
  const name = configData?.components?.oceanbase?.appname;
  const [progress, setProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(0);
  const [currentPage, setCurrentPage] = useState(true);
  const [statusData, setStatusData] = useState<API.TaskInfo>({});
  const [logData, setLogData] = useState<API.InstallLog>({});
  const navigatedToFinishedRef = useRef(false);

  const { run: fetchInstallStatus } = useRequest(queryInstallStatus, {
    onSuccess: ({ success, data }: any) => {
      if (success) {
        setStatusData(data || {});
        clearInterval(timerProgress);
        if (data?.status !== 'RUNNING' && !navigatedToFinishedRef.current) {
          navigatedToFinishedRef.current = true;
          setInstallStatus(data?.status);
          setCurrentPage(false);
          const goToFinished = async () => {
            const minDelay = new Promise((resolve) => setTimeout(resolve, 2000));
            const resultImagePreload = preloadResultImage(data?.status);
            let items: API.ConnectionInfo[] = [];
            if (data?.status === 'SUCCESSFUL') {
              [items] = await Promise.all([
                prefetchConnectionInfo(
                  name,
                  configData?.components,
                ),
                minDelay,
                resultImagePreload,
              ]);
            } else {
              await Promise.all([minDelay, resultImagePreload]);
            }
            setPrefetchedConnectInfo(items);
            setCurrentStep(7);
            setErrorVisible(false);
            setErrorsList([]);
          };
          goToFinished();
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

  const { run: handleInstallLog } = useRequest(queryInstallLog, {
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

  useEffect(() => {
    if (name) {
      fetchInstallStatus({ name });
      handleInstallLog({ name });
    }
  }, [name]);

  return (
    <InstallProcessComp
      type="OB"
      deployMode={deployMode}
      logData={logData}
      installStatus={installStatus}
      statusData={statusData}
      showProgress={showProgress}
    />
  );
}
