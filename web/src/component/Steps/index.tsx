import { CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { Space } from 'antd';
import { useEffect, useState } from 'react';
import { getLocale } from 'umi';
import EnStyles from '../../pages/Obdeploy/indexEn.less';
import ZhStyles from '../../pages/Obdeploy/indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

interface StepsProps {
  stepsItems: {
    title: string;
    key: number;
  }[];
  currentStep: number;
  showStepsKeys: number[];
}

export default function Steps({
  currentStep,
  showStepsKeys,
  stepsItems,
}: StepsProps) {
  const [showBorder, setShowBorder] = useState(false);
  const backgroundGap = locale === 'zh-CN' ? 158.75 : 181.25;
  const contentGap = locale === 'zh-CN' ? 140 : 180;
  const getIcon = (key: number) => {
    return currentStep > key ? (
      <CheckCircleOutlined className={styles.stepIcon} />
    ) : (
      <ClockCircleOutlined
        className={`${styles.stepIcon} ${styles.stepWaitIcon} ${
          currentStep === key ? styles.stepCurrentIcon : ''
        }`}
      />
    );
  };

  const handleScroll = () => {
    if (document.documentElement.scrollTop > 0) {
      setShowBorder(true);
    } else {
      setShowBorder(false);
    }
  };

  const getZhGap = () => {
    return 100;
  };
  const getEnGap = () => {
    return 0;
  };

  useEffect(() => {
    document.addEventListener('scroll', handleScroll);
  }, []);

  return (
    <div
      className={styles.stepsContainer}
      style={{ borderBottom: `${showBorder ? '1px solid #dde4ed' : '0px'}` }}
    >
      {showStepsKeys.includes(currentStep) ? (
        <div style={{ height: 120 }}>
          <div
            className={styles.stepsContent}
            style={{ width: `${showStepsKeys.length * contentGap}px` }}
          >
            <div
              className={styles.stepsBackground}
              style={{ width: `${(showStepsKeys.length - 1) * backgroundGap}px` }}
            >
              <div
                className={styles.stepsBackgroundProgress}
                style={{
                  width: `${
                    ((currentStep - 1) / (showStepsKeys.length - 1)) * 100
                  }%`,
                }}
              ></div>
            </div>
            <Space size={locale === 'zh-CN' ? getZhGap() : getEnGap()}>
              {stepsItems.map((item) => (
                <span className={styles.stepItem} key={item.key}>
                  {getIcon(item.key)}
                  <span
                    className={`${styles.stepTitle} ${
                      currentStep === item.key ? styles.stepCurrentTitle : ''
                    } ${currentStep > item.key ? styles.stepAlreadyTitle : ''}`}
                  >
                    {item.title}
                  </span>
                </span>
              ))}
            </Space>
          </div>
        </div>
      ) : null}
    </div>
  );
}
