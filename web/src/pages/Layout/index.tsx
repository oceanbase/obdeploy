import { localeList, localeText } from '@/constants';
import { intl } from '@/utils/intl';
import { requestPipeline } from '@/utils/useRequest';
import {
  GlobalOutlined,
  HomeOutlined,
  ProfileOutlined,
  ReadOutlined,
} from '@ant-design/icons';
import { ConfigProvider, Dropdown, Modal, notification, Space } from 'antd';
import type { Locale } from 'antd/es/locale-provider';
import enUS from 'antd/es/locale/en_US';
import zhCN from 'antd/es/locale/zh_CN';
import { useEffect, useState } from 'react';
import { getLocale, history, Outlet, setLocale, useModel } from 'umi';
import styles from '../Obdeploy/index.less';
import theme from '../theme';

let requestHandler;
export { requestHandler };
export default function Layout() {
  const locale = getLocale();
  const {
    OFFICAIL_WEBSITE,
    FORUMS_VISITED,
    HELP_CENTER,
    setCurrentStep,
    errorVisible,
    errorsList,
    setErrorVisible,
    setErrorsList,
  } = useModel('global');
  const [modalVisible, setModalVisible] = useState(false);
  const [token, setToken] = useState('');
  const [lastError, setLastError] = useState<API.ErrorInfo>({});
  const [modal, contextHolder] = Modal.useModal();
  const [localeConfig, setLocalConfig] = useState<Locale>(
    locale === 'zh-CN' ? zhCN : enUS,
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
  useEffect(() => {
    const newLastError = errorsList?.[errorsList?.length - 1] || null;
    if (errorVisible) {
      if (newLastError?.desc !== lastError?.desc) {
        if (newLastError?.showModal && !modalVisible) {
          setModalVisible(true);
          modal.confirm({
            title: newLastError?.title,
            content: newLastError?.desc,
            okText: intl.formatMessage({
              id: 'OBD.pages.Layout.Exit',
              defaultMessage: '退出',
            }),
            cancelText: intl.formatMessage({
              id: 'OBD.pages.Layout.ContinueToWait',
              defaultMessage: '继续等待',
            }),
            afterClose: () => {
              setModalVisible(false);
            },
            onOk: () => {
              requestPipeline.processExit = true;
              let path = history.location.pathname.split('/')[1];
              if (path === 'ocpInstaller' || path === 'update') {
                history.push(`/quit?path=${path}`);
              }
              if (path === 'obdeploy') {
                setCurrentStep(7);
              }
            },
          });
        } else {
          notification.error({
            description: newLastError?.desc,
            message: newLastError?.title,
            duration: null,
          });
        }
      }
    } else {
      notification.destroy();
    }
    setLastError(newLastError);
  }, [errorVisible, errorsList, lastError]);

  return (
    <ConfigProvider theme={theme} locale={localeConfig}>
      <div
        className={`${styles.container} ${
          locale !== 'zh-CN' ? styles.englishContainer : ''
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
              href={OFFICAIL_WEBSITE}
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
              href={FORUMS_VISITED}
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
              href={HELP_CENTER}
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
        <Outlet />
      </div>
      {contextHolder}
    </ConfigProvider>
  );
}
