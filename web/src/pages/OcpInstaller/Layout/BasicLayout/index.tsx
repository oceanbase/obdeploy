import { intl } from '@/utils/intl';
import React from 'react';
import { HomeOutlined, ReadOutlined } from '@ant-design/icons';
import { Space } from '@oceanbase/design';
import { BasicLayout as OBUIBasicLayout } from '@oceanbase/ui';
import type { BasicLayoutProps as OBUIBasicLayoutProps } from '@oceanbase/ui/es/BasicLayout';
import styles from './index.less';

interface BasicLayoutProps extends OBUIBasicLayoutProps {
  children: React.ReactNode;
  location: {
    pathname: string;
  };
}

const BasicLayout: React.FC<BasicLayoutProps> = (props) => {
  // const { isUpdate } = useSelector((state: DefaultRootState) => state.global);
  const isUpdate = false;
  // 全局菜单
  const { location, children, ...restProps } = props;

  const simpleLogoUrl = '/assets/logo/logo.png';

  return (
    <OBUIBasicLayout
      data-aspm="c323705"
      data-aspm-desc={intl.formatMessage({
        id: 'OBD.Layout.BasicLayout.InstallationDeploymentAndUpgradeSystem',
        defaultMessage: '安装部署升级系统信息',
      })}
      data-aspm-param={``}
      data-aspm-expo
      className={styles.container}
      {...restProps}
      location={location}
      simpleLogoUrl={simpleLogoUrl}
      menus={null}
      topHeader={{
        title: isUpdate
          ? intl.formatMessage({
              id: 'OBD.Layout.BasicLayout.OcpUpgradeWizardVersionNumber',
              defaultMessage: 'OCP 升级向导(版本号： 4.0.3)',
            })
          : intl.formatMessage({
              id: 'OBD.Layout.BasicLayout.OcpDeploymentWizardVersionNumber',
              defaultMessage: 'OCP 部署向导(版本号： 4.0.3)',
            }),
        extra: (
          <Space size={24}>
            <a
              className={styles.action}
              href="https://www.oceanbase.com/product/ocp"
              target="_blank"
            >
              <Space style={{ color: '#5C6B8A', cursor: 'pointer' }}>
                <HomeOutlined />
                {intl.formatMessage({
                  id: 'OBD.Layout.BasicLayout.VisitTheOfficialWebsite',
                  defaultMessage: '访问官网',
                })}
              </Space>
            </a>
            <a
              className={styles.action}
              href="https://www.oceanbase.com/"
              target="_blank"
            >
              <Space style={{ color: '#5C6B8A', cursor: 'pointer' }}>
                <ReadOutlined />
                {intl.formatMessage({
                  id: 'OBD.Layout.BasicLayout.HelpCenter',
                  defaultMessage: '帮助中心',
                })}
              </Space>
            </a>
          </Space>
        ),

        showLocale: false,
        showHelp: false,
      }}
    >
      {children}
    </OBUIBasicLayout>
  );
};

export default BasicLayout;
