import { useRef, useEffect } from 'react';

import styles from './index.less';
import bannerImg from '../../../public/assets/welcome/banner.png';

export default function Banner({title}:{title:string}) {
  const bannerRef = useRef<HTMLImageElement>(null);
  const welcomeTextRef = useRef<HTMLDivElement>(null);
  const windowResize = () => {
    welcomeTextRef.current!.style.top =
      bannerRef.current?.clientHeight! / 2 + 36 + 'px';
  };

  useEffect(() => {
    window.addEventListener('resize', windowResize);

    //待图片加载完成获取高度
    if (bannerRef.current && welcomeTextRef.current) {
      bannerRef.current.onload = function () {
        welcomeTextRef.current!.style.top =
          bannerRef.current?.clientHeight! / 2 + 36 + 'px';
      };
    }

    return () => {
      window.removeEventListener('resize', windowResize);
    };
  }, [bannerRef]);
  return (
    <div className={styles.directions}>
      <img
        ref={bannerRef}
        className={styles.banner}
        src={bannerImg}
        alt="banner"
      />
      <div ref={welcomeTextRef} className={styles.title}>
       {title}
      </div>
    </div>
  );
}
