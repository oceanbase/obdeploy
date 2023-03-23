import { useEffect } from 'react';
import { useModel } from 'umi';
import { Space, ConfigProvider } from 'antd';
import { HomeOutlined, ReadOutlined, ProfileOutlined } from '@ant-design/icons';
import useRequest from '@/utils/useRequest';
import { queryDeploymentInfoByTaskStatusType } from '@/services/ob-deploy-web/Deployments';
import Welcome from './components/Welcome';
import InstallConfig from './components/InstallConfig';
import NodeConfig from './components/NodeConfig';
import ClusterConfig from './components/ClusterConfig';
import PreCheck from './components/PreCheck';
import InstallProcess from './components/InstallProcess';
import InstallFinished from './components/InstallFinished';
import ExitPage from './components/ExitPage';
import Steps from './components/Steps';
import theme from './theme';
import styles from './index.less';

export default function IndexPage() {
  const { setCurrentStep, setConfigData, currentStep } = useModel('global');
  const { run: fetchDeploymentInfo } = useRequest(
    queryDeploymentInfoByTaskStatusType,
  );

  const contentConfig = {
    1: <InstallConfig />,
    2: <NodeConfig />,
    3: <ClusterConfig />,
    4: <PreCheck />,
    5: <InstallProcess />,
    6: <InstallFinished />,
    7: <ExitPage />,
  };

  useEffect(() => {
    fetchDeploymentInfo({ task_status: 'INSTALLING' }).then(
      ({ success, data }: API.OBResponse) => {
        if (success && data?.items?.length) {
          setCurrentStep(5);
          setConfigData({
            components: { oceanbase: { appname: data?.items[0]?.name } },
          });
        }
      },
    );
  }, []);

  const containerStyle = {
    minHeight: `${
      currentStep < 6 ? 'calc(100% - 220px)' : 'calc(100% - 50px)'
    }`,
    paddingTop: `${currentStep < 6 ? '170px' : '50px'}`,
  };

  return (
    <ConfigProvider theme={theme}>
      <header className={styles.pageHeader}>
        <img src="/assets/oceanbase.png" className={styles.logo} alt="logo" />
        <span className={styles.logoText}>部署</span>
        <Space className={styles.actionContent} size={25}>
          <a
            className={styles.action}
            href="https://www.oceanbase.com/"
            target="_blank"
            data-aspm-click="c307509.d317285"
            data-aspm-desc="顶部导航-访问官网"
            data-aspm-param={``}
            data-aspm-expo
          >
            <HomeOutlined className={styles.actionIcon} />
            访问官网
          </a>
          <a
            className={styles.action}
            href="https://ask.oceanbase.com/"
            target="_blank"
            data-aspm-click="c307509.d317284"
            data-aspm-desc="顶部导航-访问论坛"
            data-aspm-param={``}
            data-aspm-expo
          >
            <ProfileOutlined className={styles.actionIcon} />
            访问论坛
          </a>
          <a
            className={styles.action}
            href="https://www.oceanbase.com/docs/obd-cn"
            target="_blank"
            data-aspm-click="c307509.d317286"
            data-aspm-desc="顶部导航-帮助中心"
            data-aspm-param={``}
            data-aspm-expo
          >
            <ReadOutlined className={styles.actionIcon} />
            帮助中心
          </a>
        </Space>
      </header>
      <Steps />
      {currentStep === 0 ? (
        <Welcome />
      ) : (
        <div className={styles.pageContainer} style={containerStyle}>
          <main className={styles.pageMain}>
            <div className={styles.pageContent}>
              {contentConfig[currentStep]}
            </div>
          </main>
        </div>
      )}
    </ConfigProvider>
  );
}
