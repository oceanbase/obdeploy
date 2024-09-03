import { intl } from '@/utils/intl';
import { PageContainer } from '@oceanbase/ui';
import React, { useEffect, useState } from 'react';
import { useModel } from 'umi';

import CustomAlert from '@/component/CustomAlert';
import AlertMetadb from '@/component/CustomAlert/AlertMetadb';
import DeployConfig from '@/component/DeployConfig';
import InstallProcessNew from '@/component/InstallProcessNew';
import InstallResult from '@/component/InstallResult';
import MetaDBConfig from '@/component/MetaDBConfig';
import OCPConfigNew from '@/component/OCPConfigNew';
import OCPPreCheck from '@/component/OCPPreCheck';
import Steps from '@/component/Steps';
import {
  NEW_METADB_OCP_INSTALL,
  STEPS_KEYS_INSTALL,
} from '@/constant/configuration';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import { errorHandler } from '@/utils';
import { useRequest } from 'ahooks';

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

  const paddingTop = current === 2 ? 132 : current !== 6 ? 150 : 0;
  return (
    <PageContainer style={{ paddingBottom: 90, backgroundColor: '#f5f8ff' }}>
      <Steps
        currentStep={current}
        stepsItems={NEW_METADB_OCP_INSTALL}
        showStepsKeys={STEPS_KEYS_INSTALL}
      />

      <div
        style={{
          paddingTop: paddingTop,
          width: '1040px',
          margin: '0 auto',
          overflow: 'auto',
        }}
      >
        {current === 2 && (
          <>
            <CustomAlert
              type="info"
              showIcon={true}
              message={
                <p style={{ lineHeight: '22px', margin: 0 }}>
                  {intl.formatMessage({
                    id: 'OBD.OcpInstaller.Install.CreateANewMetadbMetadb',
                    defaultMessage:
                      '创建全新的 MetaDB，MetaDB 与 OCP-Server 将使用相同的主机部署服务。OCP-Server 将访问本地 MetaDB 以获得更好的服务可靠性。',
                  })}
                </p>
              }
              style={{
                margin: '16px 0',
                height: 40,
              }}
            />
            <AlertMetadb />
          </>
        )}

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
