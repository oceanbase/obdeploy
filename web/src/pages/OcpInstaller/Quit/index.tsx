import { intl } from '@/utils/intl';
import { Result, Space, Typography } from '@oceanbase/design';
import { PageContainer } from '@oceanbase/ui';
import queryString from 'query-string';
import { history } from 'umi';

import ExitPageWrapper from '@/component/ExitPageWrapper';
import PageCard from '@/component/PageCard';

import { PathType } from '@/pages/type';
import { OBD_COMMAND, OBD_COMMAND_UPGRADE } from '@/constant/configuration';
import styles from './index.less';

const { Paragraph } = Typography;

export default function Quit() {
  //@ts-ignore
  const { path } = queryString.parse(history.location.search) as
    | PathType
    | undefined;
  return (
    <ExitPageWrapper>
      <PageContainer
        className={styles.container}
        style={{ backgroundColor: '#f5f8ff' }}
      >
        <PageCard
          style={{
            height: 'calc(100vh - 72px)',
          }}
        >
          <Result
            icon={<img src="/assets/icon/success.svg" alt="" />}
            title={
              path === 'update'
                ? intl.formatMessage({
                    id: 'OBD.OcpInstaller.Quit.TheUpgradeProgramHasExited',
                    defaultMessage: '升级程序已退出',
                  })
                : intl.formatMessage({
                    id: 'OBD.OcpInstaller.Quit.TheDeploymentInstallerHasExited',
                    defaultMessage: '部署安装程序已经退出！',
                  })
            }
            subTitle={
              <Space className={styles.quitDesc}>
                {path === 'update'
                  ? intl.formatMessage({
                      id: 'OBD.OcpInstaller.Quit.TheUpgradeProgramHasQuit',
                      defaultMessage:
                        '升级程序已退出 如需再次启用升级程序，请在系统中执行',
                    })
                  : intl.formatMessage({
                      id: 'OBD.OcpInstaller.Quit.ToEnableTheDeploymentProgram',
                      defaultMessage: '如需再次启用部署程序，请在系统中执行',
                    })}

                <a
                  data-aspm={`ca48733`}
                  data-aspm-desc={intl.formatMessage({
                    id: 'OBD.OcpInstaller.Quit.ExecuteOcpN',
                    defaultMessage: '执行ocp_N',
                  })}
                  data-aspm-param={``}
                  data-aspm-expo
                >
                  <Paragraph copyable={true}>
                    {path === 'update' ? OBD_COMMAND_UPGRADE : OBD_COMMAND}
                  </Paragraph>
                </a>
              </Space>
            }
          />
        </PageCard>
      </PageContainer>
    </ExitPageWrapper>
  );
}
