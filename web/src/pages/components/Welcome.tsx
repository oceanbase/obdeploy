import { useEffect } from 'react';
import { useModel } from 'umi';
import { Button } from 'antd';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import NP from 'number-precision';
import styles from './index.less';

export default function Welcome() {
  const { setCurrentStep } = useModel('global');
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
          <h1 className={styles.h1}>欢迎您部署</h1>
          <h2 className={styles.h2}>
            <span className={styles.letter}>OceanBase</span>分布式数据库
          </h2>
          <div className={styles.startButtonContainer}>
            <Button
              className={styles.startButton}
              type="primary"
              data-aspm-click="c307505.d317276"
              data-aspm-desc="欢迎-开启体验之旅"
              data-aspm-param={``}
              data-aspm-expo
              onClick={() => setCurrentStep(1)}
            >
              开启体验之旅
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
