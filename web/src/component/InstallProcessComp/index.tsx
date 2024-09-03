import { intl } from '@/utils/intl';
import { ProCard } from '@ant-design/pro-components';
import { getLocale } from '@umijs/max';
import lottie from 'lottie-web';
import NP from 'number-precision';
import { useEffect, useState } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

interface InstallProcessCompProps {
  logData: API.InstallLog;
  installStatus: string;
  statusData: API.TaskInfo;
  showProgress: number;
}
let timerLogScroll: NodeJS.Timer | null = null;
export default function InstallProcessComp({
  logData,
  installStatus,
  statusData,
  showProgress,
}: InstallProcessCompProps) {
  const progressCoverInitWidth = 282;
  const [toBottom, setToBottom] = useState(true);
  const [progressCoverStyle, setProgreddCoverStyle] = useState({
    width: progressCoverInitWidth,
    background: '#fff',
    borderRadius: '5px',
  });
  let Video: any;

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

  const toLogBottom = () => {
    const log = document.getElementById('installLog');
    if (log) {
      log.scrollTop = log.scrollHeight;
    }
  };

  useEffect(() => {
    getAnimate();
    const log = document.querySelector('#installLog');
    log.addEventListener('scroll', handleScroll);
    return () => {
      log.removeEventListener('DOMMouseScroll', handleScroll);
      clearInterval(timerLogScroll);
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
            {intl.formatMessage({
              id: 'OBD.pages.components.InstallProcess.Deploying',
              defaultMessage: '部署中...',
            })}
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
    </ProCard>
  );
}
