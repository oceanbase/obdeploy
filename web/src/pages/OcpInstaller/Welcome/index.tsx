import { intl } from '@/utils/intl';
import { useEffect } from 'react';
import { useModel } from 'umi';
import { Button } from 'antd';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import NP from 'number-precision';
import { getLocale, history } from 'umi';
import EnStyles from '../../Obdeploy/indexEn.less';
import ZhStyles from '../../Obdeploy/indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

export default function Welcome() {
  const { setCurrentStep, setErrorVisible, setErrorsList } = useModel('global');
  let Video: any;

  const aspectRatio = NP.divide(2498, 3940).toFixed(10);

  const screenWidth = window.innerWidth * 1.3;
  let videoWidth = 0;
  let videoHeight = 0;

  if (screenWidth < 1040) {
    videoWidth = 1040;
  } else {
    videoWidth = screenWidth;
  }

  videoHeight = Math.ceil(NP.times(videoWidth, aspectRatio));

  useEffect(() => {
    const welcomeVideo = document.querySelector('.welcome-video');
    if (welcomeVideo) {
      Video = videojs(welcomeVideo, {
        controls: false,
        autoplay: true,
        loop: true,
        preload: 'auto',
      });
    }
    return () => {
      Video.dispose();
    };
  }, []);

  return (
    <div className={styles.videoContainer}>
      <div className={styles.videoContent} style={{ width: videoWidth }}>
        <div className={styles.videoActions}>
          <h1 className={styles.h1}>
            {intl.formatMessage({
              id: 'OBD.OcpInstaller.Welcome.WelcomeToTheOcpUpgrade',
              defaultMessage: '欢迎您使用 OCP 升级向导',
            })}
          </h1>
          <p className={styles.desc}>OceanBase Cloud Platfrom upgrade wizard</p>
          <div className={styles.startButtonContainer}>
            <Button
              className={styles.startButton}
              type="primary"
              onClick={() => {
                history.replace('update');
                setErrorVisible(false);
                setErrorsList([]);
              }}
            >
              {intl.formatMessage({
                id: 'OBD.OcpInstaller.Welcome.StartUpgrade',
                defaultMessage: '开始升级',
              })}
            </Button>
          </div>
        </div>
        <video
          className={`${styles.video} welcome-video video-js`}
          width={videoWidth}
          height={videoHeight}
          muted
          poster="/assets/welcome/cover.jpg"
        >
          <source src="/assets/welcome/data.mp4" type="video/mp4"></source>
        </video>
      </div>
    </div>
  );
}
