import { getDeployment } from '@/services/ob-deploy-web/Deployments';
import { getErrorInfo } from '@/utils';
import { useKeepAlive } from '@/hooks/useKeepAlive';
import useRequest from '@/utils/useRequest';
import { getLocale, useModel } from '@umijs/max';
import type { ReactNode } from 'react';
import ClusterConfig from './ClusterConfig';
import ExitPage from './ExitPage';
import styles from './index.less';
import InstallConfig from './InstallConfig';
import InstallFinished from './InstallFinished';
import InstallProcess from './InstallProcess';
import NodeConfig from './NodeConfig';
import ProgressQuit from './ProgressQuit';
import Steps from './Steps';
import PreCheckStatus from './PreCheckStatus';
import TopoCheck from './TopoCheck';

export default function IndexPage() {
  const locale = getLocale();
  const {
    setCurrentStep,
    setConfigData,
    currentStep,
    errorsList,
    setErrorVisible,
    setErrorsList,
    deployMode,
    setDeployMode,
  } = useModel('global');

  const { run: fetchDeploymentInfo } = useRequest(getDeployment, {
    onError: (e: any) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  useKeepAlive({
    currentStep,
    setCurrentStep,
    progressQuitStep: 9,
    installPhaseStepThreshold: 5,
    onInit: async () => {
      const { success, data } = await fetchDeploymentInfo({
        task_status: 'INSTALLING',
      });
      if (success && data?.items?.length) {
        setCurrentStep(5);
        setConfigData({
          components: { oceanbase: { appname: data?.items[0]?.name } },
        });
        return { skipKeepAlive: true };
      }
    },
  });

  const contentConfig: Record<number, ReactNode> = {
    1: <InstallConfig deployMode={deployMode} setDeployMode={setDeployMode} />,
    2: <NodeConfig deployMode={deployMode} />,
    3: <ClusterConfig deployMode={deployMode} />,
    4: <TopoCheck deployMode={deployMode} />,
    5: <PreCheckStatus />,
    6: <InstallProcess />,
    7: <InstallFinished />,
    8: <ExitPage />,
    9: <ProgressQuit />,
  };

  const containerStyle = {
    minHeight: `${
      currentStep < 7 ? 'calc(100% - 240px)' : 'calc(100% - 140px)'
    }`,
    paddingTop: `${currentStep < 7 ? '170px' : '70px'}`,
  };

  return (
    <div
      className={`${styles.container} ${
        locale !== 'zh-CN' ? styles.englishContainer : ''
      }`}
    >
      <Steps deployMode={deployMode} />
      <div className={styles.pageContainer} style={containerStyle}>
        <main className={styles.pageMain}>
          <div className={styles.pageContent}>{contentConfig[currentStep]}</div>
        </main>
      </div>
    </div>
  );
}
