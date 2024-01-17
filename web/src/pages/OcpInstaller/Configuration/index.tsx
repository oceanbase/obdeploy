import React, { useState, useEffect } from 'react';
import { useModel } from 'umi';
import { PageContainer } from '@oceanbase/ui';
import { useRequest } from 'ahooks';
import { errorHandler } from '@/utils';
import * as OCP from '@/services/ocp_installer_backend/OCP';
import {
  METADB_OCP_INSTALL,
  STEPS_KEYS_INSTALL,
} from '@/constant/configuration';
import Steps from '@/component/Steps';
import DeployConfig from '@/component/DeployConfig';
import ConnectConfig from '@/component/ConnectConfig';
import OCPConfigNew from '@/component/OCPConfigNew';
import OCPPreCheck from '@/component/OCPPreCheck';
import InstallProcessNew from '@/component/InstallProcessNew';
import InstallResult from '@/component/InstallResult';

const Configuration: React.FC = () => {
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
        stepsItems={METADB_OCP_INSTALL}
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
        {current === 1 && (
          <DeployConfig setCurrent={setCurrent} current={current} />
        )}

        {current === 2 && (
          <ConnectConfig setCurrent={setCurrent} current={current} />
        )}

        {current === 3 && (
          <OCPConfigNew setCurrent={setCurrent} current={current} />
        )}

        {current === 4 && (
          <OCPPreCheck setCurrent={setCurrent} current={current} />
        )}

        {current === 5 && (
          <InstallProcessNew
            id={connectId}
            current={current}
            task_id={installTaskId}
            type="install"
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

export default Configuration;
