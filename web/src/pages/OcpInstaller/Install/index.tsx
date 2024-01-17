import { intl } from '@/utils/intl';
import { useModel } from 'umi';
import React, { useState, useEffect } from 'react';
import { Alert } from 'antd';
import { PageContainer } from '@oceanbase/ui';

import { useRequest } from 'ahooks';
import { errorHandler } from '@/utils';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import { NEW_METADB_OCP_INSTALL } from '@/constant/configuration';
import DeployConfig from '@/component/DeployConfig';
import OCPPreCheck from '@/component/OCPPreCheck';
import InstallProcessNew from '@/component/InstallProcessNew';
import InstallResult from '@/component/InstallResult';
import Steps from '@/component/Steps';
import { STEPS_KEYS_INSTALL } from '@/constant/configuration';
import MetaDBConfig from '@/component/MetaDBConfig';
import OCPConfigNew from '@/component/OCPConfigNew';

const Install: React.FC = () => {
  const [current, setCurrent] = useState(1);

  const {
    connectId,
    installTaskId,
    installStatus,
    setInstallStatus,
    installResult,
  } = useModel('ocpInstallData');

  // 获取ocp 信息
  const { data: ocpInfoData, run: getInstalledOcpInfo } = useRequest(
    OCP.getInstalledOcpInfo,
    {
      manual: true,
      onError: ({ response, data }: any) => {
        errorHandler({ response, data });
      },
    },
  );

  const ocpInfo = ocpInfoData?.data || {};

  useEffect(() => {
    if (
      current == 6 &&
      installStatus === 'FINISHED' &&
      installResult === 'SUCCESSFUL'
    ) {
      getInstalledOcpInfo({
        id: connectId,
      });
    }
  }, [current, installStatus, installResult]);
  return (
    <PageContainer style={{ paddingBottom: 90,backgroundColor:'#f5f8ff' }}>
      <Steps
        currentStep={current}
        stepsItems={NEW_METADB_OCP_INSTALL}
        showStepsKeys={STEPS_KEYS_INSTALL}
      />

      <div
        style={{
          paddingTop: `${current !== 6 ? 150 : 0}px`,
          width: '1040px',
          margin: '0 auto',
          overflow: 'auto',
        }}
      >
        {current === 1 ||
          (current === 2 && (
            <Alert
              type="info"
              showIcon={true}
              message={intl.formatMessage({
                id: 'OBD.OcpInstaller.Install.CreateANewMetadbMetadb',
                defaultMessage:
                  '创建全新的 MetaDB，MetaDB 与 OCP-Server 将使用相同的主机部署服务。OCP-Server 将访问本地 MetaDB 以获得更好的服务可靠性。',
              })}
              style={{
                margin: '16px 0',
                height: 54,
              }}
            />
          ))}

        {current === 1 && (
          <DeployConfig current={current} setCurrent={setCurrent} />
        )}

        {current === 2 && (
          <MetaDBConfig current={current} setCurrent={setCurrent} />
        )}

        {current === 3 && (
          <OCPConfigNew current={current} setCurrent={setCurrent} />
        )}

        {current === 4 && (
          <OCPPreCheck current={current} setCurrent={setCurrent} />
        )}

        {current === 5 && (
          <InstallProcessNew
            id={connectId}
            current={current}
            task_id={installTaskId}
            installStatus={installStatus || ''}
            setInstallStatus={setInstallStatus}
            setCurrentStep={setCurrent}
          />
        )}

        {current === 6 && (
          <InstallResult
            current={current}
            setCurrent={setCurrent}
            ocpInfo={ocpInfo}
            installStatus={installStatus}
            installResult={installResult}
            taskId={installTaskId}
            type="install"
          />
        )}
      </div>
    </PageContainer>
  );
};

export default Install;
