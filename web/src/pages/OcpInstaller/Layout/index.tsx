import { getLocale, history } from 'umi';
import { intl } from '@/utils/intl';
import React, { useEffect } from 'react';
import { theme, ConfigProvider } from '@oceanbase/design';
import en_US from 'antd/es/locale/en_US';
import zh_CN from 'antd/es/locale/zh_CN';
import BlankLayout from './BlankLayout';
import ErrorBoundary from '@/component/ErrorBoundary';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const locale = getLocale();
  const antdLocaleMap = {
    'en-US': en_US,
    'zh-CN': zh_CN,
  };

  useEffect(() => {
    // 设置标签页的 title
    document.title = intl.formatMessage({
      id: 'OBD.OcpInstaller.Layout.OceanbaseCloudPlatform',
      defaultMessage: 'OceanBase 云平台',
    });
  }, []);

  return (
    <ConfigProvider
      navigate={history.push}
      theme={theme}
      locale={antdLocaleMap[locale] || zh_CN}
    >
      <ErrorBoundary>
        <BlankLayout>{children}</BlankLayout>
      </ErrorBoundary>
    </ConfigProvider>
  );
};

export default Layout;
