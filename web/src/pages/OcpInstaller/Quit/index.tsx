import { intl } from '@/utils/intl';
import { history } from 'umi';
import React, { useEffect } from 'react';
import { Typography, Result, Space } from '@oceanbase/design';
import { PageContainer } from '@oceanbase/ui';

import PageCard from '@/component/PageCard';
import styles from './index.less';
import { PathType } from '@/pages/type';
import ExitPageWrapper from '@/component/ExitPageWrapper';

const { Paragraph } = Typography;

export default function Quit() {
  //@ts-ignore
  const path = history.location.query.path as PathType | undefined;

  return (
    <ExitPageWrapper>
      <PageContainer className={styles.container}>
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
                    {path === 'update' ? 'obd web upgrade' : 'obd web install'}
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
