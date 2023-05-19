import { intl } from '@/utils/intl';
import { useEffect } from 'react';
import { useModel } from 'umi';
import { Button } from 'antd';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import NP from 'number-precision';
import { getLocale } from 'umi';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

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
              id: 'OBD.pages.components.Welcome.WelcomeToDeploy',
              defaultMessage: '欢迎您部署',
            })}
          </h1>
          {locale === 'zh-CN' ? (
            <h2 className={styles.h2}>
              <span className={styles.letter}>OceanBase</span>
              {intl.formatMessage({
                id: 'OBD.pages.components.Welcome.DistributedDatabase',
                defaultMessage: '分布式数据库',
              })}
            </h2>
          ) : (
            <h2 className={styles.h2}>
              {intl.formatMessage({
                id: 'OBD.pages.components.Welcome.DistributedDatabase',
                defaultMessage: '分布式数据库',
              })}
            </h2>
          )}
          <div className={styles.startButtonContainer}>
            <Button
              className={styles.startButton}
              type="primary"
              data-aspm-click="c307505.d317276"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.pages.components.Welcome.WelcomeStartTheExperienceTour',
                defaultMessage: '欢迎-开启体验之旅',
              })}
              data-aspm-param={``}
              data-aspm-expo
              onClick={() => {
                setCurrentStep(1);
                setErrorVisible(false);
                setErrorsList([]);
              }}
            >
              {intl.formatMessage({
                id: 'OBD.pages.components.Welcome.StartAnExperienceTour',
                defaultMessage: '开启体验之旅',
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
