import { intl } from '@/utils/intl';
import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Spin, Space } from '@oceanbase/design';
import { CaretRightOutlined, CaretDownOutlined } from '@ant-design/icons';
import { useRequest } from 'ahooks';
import * as Metadb from '@/services/ocp_installer_backend/Metadb';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import { errorHandler } from '@/utils';
import lottie from 'lottie-web';
import videojs from 'video.js';
import NP from 'number-precision';
import 'video.js/dist/video-js.css';
import { getLocale } from 'umi';
import styles from './index.less';
import InstallResultDisplay from '@/component/InstallResultDisplay';

export interface InstallProcessProps {
  id?: number;
  type?: 'install' | 'update';
  isReinstall?: boolean;
  installType: string;
  ocpInfo?: any;
  installInfo?: any;
  upgradeOcpInfo?: any;
  onSuccess?: () => void;
  cluster_name?: string;
  installStatus: string;
  setInstallStatus: React.Dispatch<React.SetStateAction<string>>;
  setInstallResult: React.Dispatch<React.SetStateAction<string>>;
}

let timerLogScroll: NodeJS.Timer;
let timerProgress: NodeJS.Timer;
// const locale = getLocale();
// const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;
const InstallProcess: React.FC<InstallProcessProps> = ({
  id,
  type,
  ocpInfo,
  isReinstall,
  installType,
  installInfo,
  upgradeOcpInfo,
  cluster_name,
  installStatus,
  setInstallStatus,
  setInstallResult,
}) => {
  const [toBottom, setToBottom] = useState(true);
  const [progress, setProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(0);
  const [lottieProgress, setlottieProgress] = useState();
  const [openLog, setOpenLog] = useState(false);
  const progressCoverInitWidth = 282;
  let Video: any;
  const [progressCoverStyle, setProgreddCoverStyle] = useState({
    width: progressCoverInitWidth,
    background: '#fff',
    borderRadius: '5px',
  });

  // 安装与升级
  const getInstallTaskFn =
    installType === 'OCP'
      ? type === 'update'
        ? OCP.getOcpUpgradeTask
        : OCP.getOcpInstallTask
      : Metadb.getMetadbInstallTask;
  const getInstallTaskLogFn =
    installType === 'OCP'
      ? type === 'update'
        ? OCP.getOcpUpgradeTaskLog
        : OCP.getOcpInstallTaskLog
      : Metadb.getMetadbInstallTaskLog;
  // 重装
  const getReinstallTaskFn =
    installType === 'OCP'
      ? OCP.getOcpReinstallTask
      : Metadb.getMetadbReinstallTask;
  const getreInstallTaskLogFn =
    installType === 'OCP'
      ? OCP.getOcpReinstallTaskLog
      : Metadb.getMetadbReinstallTaskLog;

  const getTaskFn = isReinstall ? getReinstallTaskFn : OCP.getOcpUpgradeTask;
  const getTaskLogFn = isReinstall
    ? getreInstallTaskLogFn
    : getInstallTaskLogFn;

  const { run: getInstallTask, data: installResultData } = useRequest(
    getTaskFn,
    {
      manual: true,
      onSuccess: ({ success, data }) => {
        if (success) {
          setOpenLog(data?.result === 'FAILED' || data?.result === 'RUNNING');
          setInstallStatus(data?.status);
          setInstallResult(data?.result);
          clearInterval(timerProgress);

          if (data?.status && data?.status === 'RUNNING') {
            setTimeout(() => {
              if (type === 'update') {
                getInstallTask({
                  cluster_name,
                  task_id: installInfo?.id,
                });
              }
            }, 2000);
          }
          // if (data.result === 'SUCCESSFUL' || data.result === 'SUCCESSFUL' || data?.status === 'FINISHED') {
          //   lottie.stop()
          // }
          const finished = data?.info?.filter(
            (item) =>
              item.status === 'FINISHED' && item.result === 'SUCCESSFUL',
          ).length;

          const newProgress = Number(
            NP.divide(finished, data?.info?.length).toFixed(2),
          );

          setProgress(newProgress);
          const step = NP.minus(newProgress, progress);
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
        errorHandler({ response, data });
        setInstallStatus('FINISHED');
        setInstallResult('FAILED');
      },
    },
  );

  const installResult = installResultData?.data || {};

  const { run: getInstallTaskLog, data: installLogData } = useRequest(
    getTaskLogFn,
    {
      manual: true,
      onSuccess: ({ success }: API.OBResponseInstallLog_) => {
        if (success && installStatus === 'RUNNING') {
          setTimeout(() => {
            getInstallTaskLog({
              cluster_name,
              task_id: installInfo?.id,
            });
          }, 2000);
        }
      },
      onError: ({ response, data }: any) => {
        errorHandler({ response, data });
        setInstallStatus('FINISHED');
        setInstallResult('FAILED');
      },
    },
  );

  const installLog = installLogData?.data || {};

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
    if (installInfo.id) {
      if (type === 'update') {
        setInstallResult('RUNNING');
        setInstallStatus('RUNNING');
        getInstallTask({
          cluster_name,
          task_id: installInfo?.id,
        });
        getInstallTaskLog({
          cluster_name,
          task_id: installInfo?.id,
        });
      }
    }
  }, [installInfo, isReinstall]);

  useEffect(() => {
    // lottie.play();
    getAnimate();
    const log = document.querySelector('#installLog');
    log.addEventListener('scroll', handleScroll);

    return () => {
      log.removeEventListener('DOMMouseScroll', handleScroll);
      clearInterval(timerLogScroll);
      clearInterval(timerProgress);
      Video.dispose();
    };
  }, [id, installInfo?.id]);

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

  useEffect(() => {
    if (lottieProgress) {
      lottieProgress.goToAndStop(
        NP.times(showProgress, lottieProgress.totalFrames - 1),
        true,
      );
    }
  }, [lottieProgress, showProgress]);

  return (
    <Card
      bordered={false}
      divided={false}
      style={{
        backgroundColor:
          installType === 'OCP' && installStatus !== 'RUNNING'
            ? '#F5F8FE'
            : '#fff',
        boxShadow: 'none',
      }}
      bodyStyle={{
        padding:
          (installType === 'OCP' && installStatus === 'RUNNING') ||
            installStatus === 'RUNNING'
            ? 24
            : 0,
      }}
    >
      <Row gutter={[24, 16]}>
        <Col span={24}>
          {installStatus === 'RUNNING' ? (
            <div
              style={{
                width: 620,
                margin: '0 auto',
              }}
            >
              <div className={styles.progressEffectContainer}>
                <span className={styles.deploymentTitle}>
                  {installType}{' '}
                  {type === 'update'
                    ? intl.formatMessage({
                      id: 'OBD.component.InstallProcess.Upgraded',
                      defaultMessage: '升级中',
                    })
                    : intl.formatMessage({
                      id: 'OBD.component.InstallProcess.Deploying',
                      defaultMessage: '部署中',
                    })}
                </span>
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
                    <source
                      src="/assets/progress/data.mp4"
                      type="video/mp4"
                    ></source>
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
              <span className={styles.deploymentName}>
                {intl.formatMessage({
                  id: 'OBD.component.InstallProcess.Deploying.1',
                  defaultMessage: '正在部署',
                })}
                {installResult?.current}
              </span>
            </div>
          ) : (
            <InstallResultDisplay
              upgradeOcpInfo={upgradeOcpInfo}
              ocpInfo={ocpInfo}
              installResult={installResult?.result}
              installStatus={installStatus}
              type={type}
              installType={installType}
            />
          )}
        </Col>
        <Col span={24}>
          <Card
            bordered={false}
            divided={false}
            title={
              <Space>
                {type === 'update'
                  ? intl.formatMessage({
                    id: 'OBD.component.InstallProcess.UpgradeLogs',
                    defaultMessage: '升级日志',
                  })
                  : intl.formatMessage({
                    id: 'OBD.component.InstallProcess.DeploymentLogs',
                    defaultMessage: '部署日志',
                  })}
                <span
                  style={{
                    cursor: 'pointer',
                  }}
                  onClick={() => {
                    setOpenLog(!openLog);
                  }}
                >
                  {openLog ? <CaretDownOutlined /> : <CaretRightOutlined />}
                </span>
              </Space>
            }
            bodyStyle={{
              padding: 24,
            }}
            className={`${styles.installSubCard} resource-card card-background-color`}
            style={{
              background: installStatus === 'RUNNING' ? '#F8FAFE' : '#fff',
            }}
          >
            <pre
              className={styles.installLog}
              id="installLog"
              style={{
                height: openLog ? (installStatus === 'FINISH' ? 302 : 360) : 0,
              }}
            >
              {openLog && (
                <>
                  {installLog?.log}
                  {installStatus === 'RUNNING' ? (
                    <div className={styles.shapeContainer}>
                      <div className={styles.shape} />
                      <div className={styles.shape} />
                      <div className={styles.shape} />
                      <div className={styles.shape} />
                    </div>
                  ) : null}

                  <div style={{ height: 60 }}>
                    <Spin spinning={installStatus === 'RUNNING'} />
                  </div>
                </>
              )}
            </pre>
          </Card>
        </Col>
      </Row>
    </Card>
  );
};

export default InstallProcess;
