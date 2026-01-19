import { getLocale, history } from 'umi';
import { intl } from '@/utils/intl';
import NP from 'number-precision';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import { useEffect } from 'react';
import { Button } from 'antd';

import EnStyles from './Obdeploy/indexEn.less';
import ZhStyles from './Obdeploy/indexZh.less';
import { getTailPath } from '@/utils/helper';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;
export default function IndexPage() {
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
      if (Video) {
        Video.dispose();
      }
    };
  }, []);

  const taiPath = getTailPath();
  const isUpgrade = taiPath.includes('update');

  return (
    <div className={styles.videoContainer}>
      <div className={styles.videoContent} style={{ width: videoWidth }}>
        <div className={styles.videoActions}>

          <h1 className={styles.h1}>
            {
              isUpgrade ? (
                intl.formatMessage({
                  id: 'OBD.OcpInstaller.Welcome.WelcomeToTheOcpUpgrade',
                  defaultMessage: '欢迎您使用 OceanBase 升级向导',
                })
              ) : (
                intl.formatMessage({
                  id: 'OBD.pages.components.Welcome.WelcomeToDeploy',
                  defaultMessage: '欢迎您部署',
                })
              )
            }
          </h1>
          {
            !isUpgrade ? (
              <>
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
              </>
            ) : (
              null
            )
          }

          <p className={styles.desc}>
            {
              isUpgrade ? 'OceanBase Upgrade Wizard' : 'OceanBase comprehensive database'
            }
          </p>
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
                if (isUpgrade) {
                  history.push('/guide?update');
                } else {
                  history.push('/guide');
                }
              }}
            >
              {
                isUpgrade ? (
                  intl.formatMessage({
                    id: 'OBD.OcpInstaller.Welcome.StartUpgrade',
                    defaultMessage: '开始升级',
                  })
                ) : (
                  intl.formatMessage({
                    id: 'OBD.pages.components.Welcome.StartAnExperienceTour',
                    defaultMessage: '开启体验之旅',
                  })
                )
              }
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
  )
}