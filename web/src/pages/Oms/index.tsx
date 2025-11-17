
import { getLocale, useModel } from 'umi';
import ExitPage from './ExitPage';
import styles from './index.less';
import InstallConfig from './InstallConfig';
import InstallFinished from './InstallFinished';
import InstallProcess from './InstallProcess';
import NodeConfig from './NodeConfig';
import ProgressQuit from './ProgressQuit';
import Steps from './Steps';
import ConnectionInfo from './Update/Component/ConnectionInfo';
import PreCheckStatus from './PreCheckStatus';

export default function IndexPage() {
  const locale = getLocale();
  const {
    currentStep,
  } = useModel('global');


  const contentConfig = {
    1: <InstallConfig />,
    2: <NodeConfig />,
    3: <ConnectionInfo type={'install'} />,
    4: <PreCheckStatus />,
    5: <InstallProcess />,
    6: <InstallFinished />,
    7: <ExitPage />,
    8: <ProgressQuit />,
  };


  const containerStyle = {
    minHeight: `${currentStep < 6 ? 'calc(100% - 240px)' : 'calc(100% - 140px)'
      }`,
    paddingTop: `${currentStep < 6 ? '170px' : '70px'}`,
  };

  return (
    <div
      className={`${styles.container} ${locale !== 'zh-CN' ? styles.englishContainer : ''
        }`}
    >
      <Steps />
      <div className={styles.pageContainer} style={containerStyle}>
        <main className={styles.pageMain}>
          <div className={styles.pageContent}>{contentConfig[currentStep]}</div>
        </main>
      </div>
    </div>
  );
}
