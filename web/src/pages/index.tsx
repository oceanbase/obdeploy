import { intl } from '@/utils/intl';
import { useEffect, useState } from 'react';
import { useModel } from 'umi';
import { Space, ConfigProvider, notification, Dropdown, Modal } from 'antd';
import {
  HomeOutlined,
  ReadOutlined,
  ProfileOutlined,
  GlobalOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import useRequest from '@/utils/useRequest';
import { getErrorInfo, getRandomPassword } from '@/utils';
import { getDeployment } from '@/services/ob-deploy-web/Deployments';
import { validateOrSetKeepAliveToken } from '@/services/ob-deploy-web/Common';
import Welcome from './components/Welcome';
import InstallConfig from './components/InstallConfig';
import NodeConfig from './components/NodeConfig';
import ClusterConfig from './components/ClusterConfig';
import PreCheck from './components/PreCheck';
import InstallProcess from './components/InstallProcess';
import InstallFinished from './components/InstallFinished';
import ExitPage from './components/ExitPage';
import ProgressQuit from './components/ProgressQuit';
import Steps from './components/Steps';
import { localeList, localeText } from '@/constants';
import type { Locale } from 'antd/es/locale';
import { setLocale, getLocale } from 'umi';
import enUS from 'antd/es/locale/en_US';
import zhCN from 'antd/es/locale/zh_CN';
import theme from './theme';
import styles from './index.less';

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
  } = useModel('global');
  const [lastError, setLastError] = useState<API.ErrorInfo>({});
  const [first, setFirst] = useState(true);
  const [token, setToken] = useState('');
  const [isInstall, setIsInstall] = useState(false);
  const [localeConfig, setLocalConfig] = useState<Locale>(
    locale === 'zh-CN' ? zhCN : enUS,
  );

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
            if (!isInstall) {
              handleValidateOrSetKeepAliveToken({
                token: token,
                is_clear: true,
              });
              setIsInstall(true);
            }
          } else {
            setTimeout(() => {
              handleValidateOrSetKeepAliveToken({ token });
            }, 1000);
          }
          setFirst(false);
        }
      },
      onError: () => {
        if (currentStep > 4) {
          handleValidateOrSetKeepAliveToken({ token: token, is_clear: true });
        } else {
          setTimeout(() => {
            handleValidateOrSetKeepAliveToken({ token });
          }, 1000);
        }
      },
    },
  );

  const setCurrentLocale = (key: string) => {
    if (key !== locale) {
      setLocale(key);
      window.localStorage.setItem('uuid', token);
    }
    setLocalConfig(key === 'zh-CN' ? zhCN : enUS);
  };

  const getLocaleItems = () => {
    return localeList.map((item) => ({
      ...item,
      label: <a onClick={() => setCurrentLocale(item.key)}>{item.label}</a>,
    }));
  };

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
    let token = '';
    fetchDeploymentInfo({ task_status: 'INSTALLING' }).then(
      ({ success, data }: API.OBResponse) => {
        if (success && data?.items?.length) {
          setCurrentStep(5);
          setConfigData({
            components: { oceanbase: { appname: data?.items[0]?.name } },
          });
        } else {
          if (uuid) {
            token = uuid;
          } else {
            token = `${Date.now()}${getRandomPassword(true)}`;
          }
          setToken(token);
          handleValidateOrSetKeepAliveToken({ token });
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

  useEffect(() => {
    const newLastError = errorsList?.[errorsList?.length - 1] || null;
    if (errorVisible) {
      if (newLastError?.desc !== lastError?.desc) {
        notification.error({
          description: newLastError?.desc,
          message: newLastError?.title,
          duration: null,
        });
      }
    } else {
      notification.destroy();
    }
    setLastError(newLastError);
  }, [errorVisible, errorsList, lastError]);

  const containerStyle = {
    minHeight: `${currentStep < 6 ? 'calc(100% - 240px)' : 'calc(100% - 140px)'
      }`,
    paddingTop: `${currentStep < 6 ? '170px' : '70px'}`,
  };

  return (
    <ConfigProvider theme={theme} locale={localeConfig}>
      <div
        className={`${styles.container} ${locale !== 'zh-CN' ? styles.englishContainer : ''
          }`}
      >
        <header className={styles.pageHeader}>
          <img src="/assets/oceanbase.png" className={styles.logo} alt="logo" />
          <span className={styles.logoText}>
            {intl.formatMessage({
              id: 'OBD.src.pages.DeploymentWizard',
              defaultMessage: '部署向导',
            })}
          </span>
          <Space className={styles.actionContent} size={25}>
            <Dropdown menu={{ items: getLocaleItems() }}>
              <a
                className={styles.action}
                onClick={(e) => e.preventDefault()}
                data-aspm-click="c307509.d326700"
                data-aspm-desc={intl.formatMessage({
                  id: 'OBD.src.pages.TopNavigationSwitchBetweenChinese',
                  defaultMessage: '顶部导航-中英文切换',
                })}
                data-aspm-param={``}
                data-aspm-expo
              >
                <GlobalOutlined className={styles.actionIcon} />
                {localeText[locale]}
              </a>
            </Dropdown>
            <a
              className={styles.action}
              href="https://www.oceanbase.com/"
              target="_blank"
              data-aspm-click="c307509.d317285"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.src.pages.TopNavigationVisitTheOfficial',
                defaultMessage: '顶部导航-访问官网',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              <HomeOutlined className={styles.actionIcon} />
              {intl.formatMessage({
                id: 'OBD.src.pages.VisitTheOfficialWebsite',
                defaultMessage: '访问官网',
              })}
            </a>
            <a
              className={styles.action}
              href="https://ask.oceanbase.com/"
              target="_blank"
              data-aspm-click="c307509.d317284"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.src.pages.TopNavigationAccessForum',
                defaultMessage: '顶部导航-访问论坛',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              <ProfileOutlined className={styles.actionIcon} />
              {intl.formatMessage({
                id: 'OBD.src.pages.VisitTheForum',
                defaultMessage: '访问论坛',
              })}
            </a>
            <a
              className={styles.action}
              href="https://www.oceanbase.com/docs/obd-cn"
              target="_blank"
              data-aspm-click="c307509.d317286"
              data-aspm-desc={intl.formatMessage({
                id: 'OBD.src.pages.TopNavigationHelpCenter',
                defaultMessage: '顶部导航-帮助中心',
              })}
              data-aspm-param={``}
              data-aspm-expo
            >
              <ReadOutlined className={styles.actionIcon} />
              {intl.formatMessage({
                id: 'OBD.src.pages.HelpCenter',
                defaultMessage: '帮助中心',
              })}
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
      </div>
    </ConfigProvider>
  );
}
