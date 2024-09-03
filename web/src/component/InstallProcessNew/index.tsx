import EnStyles from '@/pages/Obdeploy/indexEn.less';
import ZhStyles from '@/pages/Obdeploy/indexZh.less';
import {
  queryInstallLog,
  queryInstallStatus,
} from '@/services/ob-deploy-web/Deployments';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import { getErrorInfo } from '@/utils';
import { intl } from '@/utils/intl';
import useCustomRequest, { requestPipeline } from '@/utils/useRequest';
import { ProCard } from '@ant-design/pro-components';
import lottie from 'lottie-web';
import NP from 'number-precision';
import { useEffect, useState } from 'react';
import { getLocale, useModel } from 'umi';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import CustomFooter from '../CustomFooter';
import ExitBtn from '../ExitBtn';

interface InstallProcessNewProps {
  current: number;
  setCurrentStep: React.Dispatch<React.SetStateAction<number>>;
  name?: string;
  id?: number; //connectId
  task_id?: number;
  type?: 'install' | 'update';
  installStatus: string;
  setInstallStatus: React.Dispatch<React.SetStateAction<string>>;
  cluster_name?: string;
}

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

let timerLogScroll: NodeJS.Timer;
let timerProgress: NodeJS.Timer;

export default function InstallProcessNew({
  setCurrentStep,
  name,
  current,
  id,
  task_id,
  installStatus,
  setInstallStatus,
  type,
  cluster_name,
}: InstallProcessNewProps) {
  const { setErrorVisible, setErrorsList, errorsList } = useModel('global');
  const { setInstallResult, isReinstall, logData, setLogData } =
    useModel('ocpInstallData');
  const progressCoverInitWidth = 282;
  const [toBottom, setToBottom] = useState(true);
  const [progress, setProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(0);
  const [progressCoverStyle, setProgreddCoverStyle] = useState({
    width: progressCoverInitWidth,
    background: '#fff',
    borderRadius: '5px',
  });
  const [currentPage, setCurrentPage] = useState(true);
  const [statusData, setStatusData] = useState<API.TaskInfo>({});
  const [opcStatusData, setOpcStatusData] = useState<any>({});
  let Video: any;

  const getInstallTaskFn =
    type === 'update' ? OCP.getOcpUpgradeTask : OCP.getOcpInstallTask;
  const getInstallTaskLogFn =
    type === 'update' ? OCP.getOcpUpgradeTaskLog : OCP.getOcpInstallTaskLog;
  const getReinstallTaskFn = OCP.getOcpReinstallTask;
  const getreInstallTaskLogFn = OCP.getOcpReinstallTaskLog;
  const getTaskFn = isReinstall ? getReinstallTaskFn : getInstallTaskFn;
  const getTaskLogFn = isReinstall
    ? getreInstallTaskLogFn
    : getInstallTaskLogFn;

  const { run: fetchInstallStatus } = useCustomRequest(queryInstallStatus, {
    onSuccess: ({ success, data }: API.OBResponseTaskInfo_) => {
      if (success) {
        setStatusData(data || {});
        clearInterval(timerProgress);
        if (data?.status !== 'RUNNING') {
          setInstallStatus(data?.status);
          setCurrentPage(false);
          setTimeout(() => {
            setCurrentStep(current + 1);
            setErrorVisible(false);
            setErrorsList([]);
          }, 2000);
        } else {
          setTimeout(() => {
            fetchInstallStatus({ name });
          }, 2000);
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
        }, 2000);
      }
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  const { run: handleInstallLog } = useCustomRequest(queryInstallLog, {
    onSuccess: ({ success, data }: API.OBResponseInstallLog_) => {
      if (success && installStatus === 'RUNNING') {
        setLogData(data || {});
        setTimeout(() => {
          handleInstallLog({ name });
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
          handleInstallLog({ name });
        }, 2000);
      }
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });
  // ocp
  const { run: getInstallTask } = useCustomRequest(getTaskFn, {
    manual: true,
    onSuccess: ({ success, data }) => {
      if (success) {
        setOpcStatusData(data || {});
        clearInterval(timerProgress);
        setInstallResult(data?.result);
        if (data?.status && data?.status !== 'RUNNING') {
          setInstallStatus(data?.status);
          setCurrentPage(false);
          setTimeout(() => {
            setCurrentStep(current + 1);
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
  const { run: getInstallTaskLog } = useCustomRequest(getTaskLogFn, {
    manual: true,
    onSuccess: ({ success, data }: API.OBResponseInstallLog_) => {
      if (success) setLogData(data || {});
      if (success && installStatus === 'RUNNING') {
        setTimeout(() => {
          if (type === 'update') {
            getInstallTaskLog({ cluster_name, task_id });
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
          if (type === 'update') {
            getInstallTaskLog({ cluster_name, task_id });
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

    if (progressAnimate) {
      Video = videojs(progressAnimate, {
        controls: false,
        autoplay: true,
        loop: true,
        preload: 'auto',
      });
    }

    lottie.loadAnimation({
      prefetch: true,
      container: computerAnimate,
      renderer: 'svg',
      loop: true,
      autoplay: true,
      path: '/assets/computer/data.json',
    });

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
    } else if (id && task_id) {
      setInstallResult('RUNNING');
      setInstallStatus('RUNNING');
      getInstallTask({ id, task_id });
      if (type === 'update') {
        getInstallTaskLog({ cluster_name, task_id });
      } else {
        getInstallTaskLog({ id, task_id });
      }
    }
  }, [name, id, task_id]);

  useEffect(() => {
    getAnimate();
    const log = document.querySelector('#installLog');
    log.addEventListener('scroll', handleScroll);
    return () => {
      log.removeEventListener('DOMMouseScroll', handleScroll);
      clearInterval(timerLogScroll);
      clearInterval(timerProgress);
      Video.dispose();
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
    let newCoverStyle: any = { ...progressCoverStyle };
    const newCoverWidth = NP.times(
      NP.minus(1, showProgress),
      progressCoverInitWidth,
    );

    if (showProgress > 0) {
      newCoverStyle = {
        width: `${newCoverWidth}px`,
        background:
          'linear-gradient( to right, rgba(255, 255, 255, 0), rgba(255, 255, 255, 1) 10px, rgba(255, 255, 255, 1) )',
      };
    }
    setProgreddCoverStyle(newCoverStyle);
  }, [showProgress]);

  const getText = (name?: string) => {
    return intl.formatMessage(
      {
        id: 'OBD.pages.components.InstallProcess.DeployingName',
        defaultMessage: '正在部署 {name}',
      },
      { name: name },
    );
  };
  return (
    <ProCard direction="column" className="card-padding-bottom-24">
      <ProCard>
        <div className={styles.progressEffectContainer}>
          <div className={styles.deployTitle}>
            {type === 'update' ? (
              <>
                {intl.formatMessage({
                  id: 'OBD.component.InstallProcessNew.Upgrading',
                  defaultMessage: '升级中...',
                })}
              </>
            ) : (
              <>
                {' '}
                {intl.formatMessage({
                  id: 'OBD.pages.components.InstallProcess.Deploying',
                  defaultMessage: '部署中...',
                })}
              </>
            )}
          </div>
          <div className={styles.computer}>
            <div
              className={`computer-animate ${styles.computerAnimate} `}
              data-anim-path="/assets/computer/data.json"
            ></div>
          </div>
          <div className={styles.progress}>
            <video
              className={`${styles.progressVedio} progress-animate video-js`}
              muted
            >
              <source src="/assets/progress/data.mp4" type="video/mp4"></source>
            </video>
            <div
              className={styles.progressCover}
              style={{ ...progressCoverStyle }}
            >
              <div className={styles.progressStart}></div>
            </div>
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
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.pages.components.InstallProcess.DeployingDeploying',
            defaultMessage: '部署中-正在部署',
          })}
          data-aspm-param={``}
          data-aspm-expo
        >
          {getText(statusData?.current)}
        </span>
      </ProCard>
      <ProCard
        title={intl.formatMessage({
          id: 'OBD.pages.components.InstallProcess.DeploymentLogs',
          defaultMessage: '部署日志',
        })}
        className={styles.installSubCard}
      >
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
      <CustomFooter>
        <ExitBtn />
      </CustomFooter>
    </ProCard>
  );
}
