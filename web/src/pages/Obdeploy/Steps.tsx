import { intl } from '@/utils/intl';
import { useModel } from 'umi';
import { Space } from 'antd';
import { ClockCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { getLocale } from 'umi';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;
import { useEffect, useState } from 'react';

export default function Steps() {
  const { currentStep } = useModel('global');
  const [showBorder, setShowBorder] = useState(false);

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

  const getStepsItems = () => {
    return [
      {
        title: intl.formatMessage({
          id: 'OBD.pages.components.Steps.DeploymentConfiguration',
          defaultMessage: '部署配置',
        }),
        key: 1,
        icon: getIcon(1),
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.components.Steps.NodeConfiguration',
          defaultMessage: '节点配置',
        }),
        key: 2,
        icon: getIcon(2),
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.components.Steps.ClusterConfiguration',
          defaultMessage: '集群配置',
        }),
        key: 3,
        icon: getIcon(3),
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.components.Steps.PreCheck',
          defaultMessage: '预检查',
        }),
        key: 4,
        icon: getIcon(4),
      },
      {
        title: intl.formatMessage({
          id: 'OBD.pages.components.Steps.Deployment',
          defaultMessage: '部署',
        }),
        key: 5,
        icon: getIcon(5),
      },
    ];
  };

  const showStepsKeys = [1, 2, 3, 4, 5];

  const handleScroll = () => {
    if (document.documentElement.scrollTop > 0) {
      setShowBorder(true);
    } else {
      setShowBorder(false);
    }
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
          <div className={styles.stepsContent}>
            <div className={styles.stepsBackground}>
              <div
                className={styles.stepsBackgroundProgress}
                style={{ width: `${(currentStep - 1) * 25}%` }}
              ></div>
            </div>
            <Space size={locale === 'zh-CN' ? 100 : 0}>
              {getStepsItems().map((item) => (
                <span className={styles.stepItem} key={item.key}>
                  {item.icon}
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
