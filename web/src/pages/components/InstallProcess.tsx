import { useEffect, useState } from 'react';
import { useModel } from 'umi';
import { ProCard } from '@ant-design/pro-components';
import useRequest from '@/utils/useRequest';
import {
  queryInstallStatus,
  queryInstallLog,
} from '@/services/ob-deploy-web/Deployments';
import { handleResponseError } from '@/utils';
import lottie from 'lottie-web';
import NP from 'number-precision';
import styles from './index.less';

let timerLogScroll: NodeJS.Timer;
let timerProgress: NodeJS.Timer;

export default function InstallProcess() {
  const { setCurrentStep, configData, installStatus, setInstallStatus } =
    useModel('global');
  const name = configData?.components?.oceanbase?.appname;
  const [toBottom, setToBottom] = useState(true);
  const [progress, setProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(0);
  const [lottieProgress, setlottieProgress] = useState();
  const [lastError, setLastError] = useState('');
  const [currentPage, setCurrentPage] = useState(true);

  const { run: fetchInstallStatus, data: statusData } = useRequest(
    queryInstallStatus,
    {
      skipStatusError: true,
      onSuccess: ({ success, data }: API.OBResponseTaskInfo_) => {
        if (success) {
          clearInterval(timerProgress);
          if (data?.status !== 'RUNNING') {
            setInstallStatus(data?.status);
            setCurrentPage(false);
            setTimeout(() => {
              setCurrentStep(6);
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
      onError: ({ response, data }: any) => {
        if (currentPage) {
          setTimeout(() => {
            fetchInstallStatus({ name });
          }, 1000);
        }
        const errorInfo = data?.msg || data?.detail || response?.statusText;
        const errorInfoStr = errorInfo ? JSON.stringify(errorInfo) : '';
        if (errorInfo && lastError !== errorInfoStr) {
          setLastError(errorInfoStr);
          handleResponseError(errorInfo);
        }
      },
    },
  );

  const { run: handleInstallLog, data: logData } = useRequest(queryInstallLog, {
    skipStatusError: true,
    onSuccess: ({ success }: API.OBResponseInstallLog_) => {
      if (success && installStatus === 'RUNNING') {
        setTimeout(() => {
          handleInstallLog({ name });
        }, 1000);
      }
    },
    onError: ({ response, data }: any) => {
      if (installStatus === 'RUNNING' && currentPage) {
        setTimeout(() => {
          handleInstallLog({ name });
        }, 1000);
      }
      const errorInfo = data?.msg || data?.detail || response?.statusText;
      const errorInfoStr = errorInfo ? JSON.stringify(errorInfo) : '';
      if (errorInfoStr && lastError !== errorInfoStr) {
        setLastError(errorInfoStr);
        handleResponseError(errorInfo);
      }
    },
  });

  const toLogBottom = () => {
    const log = document.getElementById('installLog');
    if (log) {
      log.scrollTop = log.scrollHeight;
    }
  };

  const handleScroll = (e?: any) => {
    e = e || window.event;
    const dom = e.target;
    if (dom.scrollTop + dom.clientHeight === dom.scrollHeight) {
      setToBottom(true);
    } else {
      setToBottom(false);
    }
  };

  const getAnimate = () => {
    const computerAnimate = document.querySelector('.computer-animate');
    const progressAnimate = document.querySelector('.progress-animate');
    const spacemanAnimate = document.querySelector('.spaceman-animate');
    const sqlAnimate = document.querySelector('.database-animate');

    lottie.loadAnimation({
      prefetch: true,
      container: computerAnimate,
      renderer: 'svg',
      loop: true,
      autoplay: true,
      path: '/assets/computer/data.json',
    });

    setlottieProgress(
      lottie.loadAnimation({
        prefetch: true,
        container: progressAnimate,
        renderer: 'svg',
        loop: false,
        autoplay: false,
        path: '/assets/progress/data.json',
      }),
    );

    lottie.loadAnimation({
      prefetch: true,
      container: spacemanAnimate,
      renderer: 'svg',
      loop: true,
      autoplay: true,
      path: '/assets/spaceman/data.json',
    });
    lottie.loadAnimation({
      prefetch: true,
      container: sqlAnimate,
      renderer: 'svg',
      loop: true,
      autoplay: true,
      path: '/assets/database/data.json',
    });
  };

  useEffect(() => {
    if (name) {
      fetchInstallStatus({ name });
      handleInstallLog({ name });
    }
  }, [name]);

  useEffect(() => {
    getAnimate();
    const log = document.querySelector('#installLog');
    log.addEventListener('scroll', handleScroll);
    return () => {
      log.removeEventListener('DOMMouseScroll', handleScroll);
      clearInterval(timerLogScroll);
      clearInterval(timerProgress);
    };
  }, []);

  useEffect(() => {
    if (toBottom) {
      toLogBottom();
      timerLogScroll = setInterval(() => toLogBottom());
    } else {
      clearInterval(timerLogScroll);
    }
  }, [toBottom]);

  useEffect(() => {
    if (lottieProgress) {
      lottieProgress.goToAndStop(
        NP.times(showProgress, lottieProgress.totalFrames - 1),
        true,
      );
    }
  }, [lottieProgress, showProgress]);

  return (
    <ProCard direction="column" className="card-padding-bottom-24">
      <ProCard>
        <div className={styles.progressEffectContainer}>
          <div className={styles.computer}>
            <div
              className={`computer-animate ${styles.computerAnimate}`}
              data-anim-path="/assets/computer/data.json"
            ></div>
          </div>
          <div className={styles.progress}>
            <div
              className={`progress-animate ${styles.progressAnimate}`}
              data-anim-path="/assets/progress/data.json"
            ></div>
          </div>
          <div className={styles.spaceman}>
            <div
              className={`spaceman-animate ${styles.spacemanAnimate}`}
              data-anim-path="/assets/spaceman/data.json"
            ></div>
          </div>
          <div className={styles.database}>
            <div
              className={`database-animate ${styles.sqlAnimate}`}
              data-anim-path="/assets/database/data.json"
            ></div>
          </div>
        </div>
        <span
          className={styles.deploymentName}
          data-aspm-click="c307512.d317290"
          data-aspm-desc="部署中-正在部署"
          data-aspm-param={``}
          data-aspm-expo
        >
          正在部署 {statusData?.current}
        </span>
      </ProCard>
      <ProCard title="部署日志" className={styles.installSubCard}>
        <pre className={styles.installLog} id="installLog">
          {logData?.log}
          {installStatus === 'RUNNING' ? (
            <div className={styles.shapeContainer}>
              <div className={styles.shape}></div>
              <div className={styles.shape}></div>
              <div className={styles.shape}></div>
              <div className={styles.shape}></div>
            </div>
          ) : null}
        </pre>
      </ProCard>
    </ProCard>
  );
}
