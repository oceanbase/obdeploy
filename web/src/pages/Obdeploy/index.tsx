import { validateOrSetKeepAliveToken } from '@/services/ob-deploy-web/Common';
import { getDeployment } from '@/services/ob-deploy-web/Deployments';
import { getErrorInfo, getRandomPassword } from '@/utils';
import { intl } from '@/utils/intl';
import useRequest, { requestPipeline } from '@/utils/useRequest';
import { InfoCircleOutlined } from '@ant-design/icons';
import { Modal } from 'antd';
import { useEffect, useState } from 'react';
import { getLocale, useModel } from 'umi';
import ClusterConfig from './ClusterConfig';
import ExitPage from './ExitPage';
import styles from './index.less';
import InstallConfig from './InstallConfig';
import InstallFinished from './InstallFinished';
import InstallProcess from './InstallProcess';
import NodeConfig from './NodeConfig';
import PreCheck from './PreCheck';
import ProgressQuit from './ProgressQuit';
import Steps from './Steps';

export default function IndexPage() {
  const uuid = window.localStorage.getItem('uuid');
  const locale = getLocale();
  const {
    setCurrentStep,
    setConfigData,
    currentStep,
    errorVisible,
    errorsList,
    setErrorVisible,
    setErrorsList,
    first,
    setFirst,
    token,
    setToken,
    aliveTokenTimer,
  } = useModel('global');
  const [isInstall, setIsInstall] = useState(false);

  const { run: fetchDeploymentInfo } = useRequest(getDeployment, {
    onError: (e: any) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });

  const { run: handleValidateOrSetKeepAliveToken } = useRequest(
    validateOrSetKeepAliveToken,
    {
      onSuccess: ({ success, data }: API.OBResponse) => {
        if (success) {
          if (!data) {
            if (first) {
              Modal.confirm({
                className: 'new-page-confirm',
                title: intl.formatMessage({
                  id: 'OBD.src.pages.ItIsDetectedThatYou',
                  defaultMessage:
                    '检测到您打开了一个新的部署流程页面，请确认是否使用新页面继续部署工作？',
                }),
                width: 424,
                icon: <InfoCircleOutlined />,
                content: intl.formatMessage({
                  id: 'OBD.src.pages.UseTheNewPageTo',
                  defaultMessage:
                    '使用新的页面部署，原部署页面将无法再提交任何部署请求',
                }),
                onOk: () => {
                  handleValidateOrSetKeepAliveToken({ token, overwrite: true });
                },
                onCancel: () => {
                  setCurrentStep(8);
                },
              });
              setTimeout(() => {
                document.activeElement.blur();
              }, 100);
            } else {
              setCurrentStep(8);
            }
          } else if (currentStep > 4) {
            if (!isInstall && !requestPipeline.processExit) {
              handleValidateOrSetKeepAliveToken({
                token: token,
                is_clear: true,
              });
              setIsInstall(true);
            }
          } else {
            if (!requestPipeline.processExit)
              aliveTokenTimer.current = setTimeout(() => {
                handleValidateOrSetKeepAliveToken({ token });
              }, 1000);
          }
          setFirst(false);
        }
      },
      onError: (err: any) => {
        if (err?.errorPipeline.length >= 5) {
          const errorInfo = getErrorInfo(err);
          setErrorVisible(true);
          setErrorsList([...errorsList, errorInfo]);
        }
        if (currentStep > 4 && !requestPipeline.processExit) {
          handleValidateOrSetKeepAliveToken({ token: token, is_clear: true });
        } else {
          // 进程可能退出，停止轮询
          if (requestPipeline.processExit) return;
          aliveTokenTimer.current = setTimeout(() => {
            handleValidateOrSetKeepAliveToken({ token });
          }, 1000);
        }
      },
    },
  );

  const contentConfig = {
    1: <InstallConfig />,
    2: <NodeConfig />,
    3: <ClusterConfig />,
    4: <PreCheck />,
    5: <InstallProcess />,
    6: <InstallFinished />,
    7: <ExitPage />,
    8: <ProgressQuit />,
  };

  useEffect(() => {
    let newToken = '';
    fetchDeploymentInfo({ task_status: 'INSTALLING' }).then(
      ({ success, data }: API.OBResponse) => {
        if (success && data?.items?.length) {
          setCurrentStep(5);
          setConfigData({
            components: { oceanbase: { appname: data?.items[0]?.name } },
          });
        } else {
          if (!token) {
            if (uuid) {
              newToken = uuid;
            } else {
              newToken = `${Date.now()}${getRandomPassword(true)}`;
            }
            setToken(newToken);
            handleValidateOrSetKeepAliveToken({ token: newToken });
          } else {
            handleValidateOrSetKeepAliveToken({ token });
          }
          window.localStorage.setItem('uuid', '');
        }
      },
    );
    const sendBeacon = () => {
      const url =
        window.location.origin +
        '/api/v1/connect/keep_alive?token=' +
        token +
        '&is_clear=true';
      navigator.sendBeacon(url);
    };
    window.addEventListener('beforeunload', function (e) {
      sendBeacon();
    });
  }, []);

  const containerStyle = {
    minHeight: `${
      currentStep < 6 ? 'calc(100% - 240px)' : 'calc(100% - 140px)'
    }`,
    paddingTop: `${currentStep < 6 ? '170px' : '70px'}`,
  };

  return (
    <div
      className={`${styles.container} ${
        locale !== 'zh-CN' ? styles.englishContainer : ''
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
