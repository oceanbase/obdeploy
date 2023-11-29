import { ConfigProvider, Space, Dropdown } from 'antd';
import { ReactElement, useState } from 'react';
import type { Locale } from 'antd/es/locale-provider';
import enUS from 'antd/es/locale/en_US';
import zhCN from 'antd/es/locale/zh_CN';
import { getLocale, setLocale } from 'umi';
import {
  HomeOutlined,
  ReadOutlined,
  ProfileOutlined,
  GlobalOutlined,
} from '@ant-design/icons';

import { intl } from '@/utils/intl';
import { localeList, localeText } from '@/constants';
import theme from '../theme';
import styles from '../Obdeploy/index.less';

export default function Layout(props: React.PropsWithChildren<ReactElement>) {
  const locale = getLocale();
  const [token, setToken] = useState('');
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
        {props.children}
      </div>
    </ConfigProvider>
  );
}
