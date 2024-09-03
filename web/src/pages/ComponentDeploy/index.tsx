import Steps from '@/component/Steps';
import {
  COMPONENT_INSTALL,
  STEPS_KEYS_COMP_INSTALL,
} from '@/constant/configuration';
import { componentChangeDeploymentsName } from '@/services/component-change/componentChange';
import { PageContainer } from '@ant-design/pro-components';
import { useModel } from '@umijs/max';
import { useRequest } from 'ahooks';
import { useEffect } from 'react';
import ExitPage from '../Obdeploy/ExitPage';
import ComponentConfig from './ComponentConfig';
import DeployConfig from './DeployConfig';
import Install from './Install';
import PreCheck from './PreCheck';
export default function ComponentDeploy() {
  const { current } = useModel('componentDeploy');

  const { data: clusterListsRes, run: getClusterList } = useRequest(
    componentChangeDeploymentsName,
  );
  const STEP_CONFIG = {
    1: <DeployConfig clusterList={clusterListsRes?.data} />,
    2: <ComponentConfig />,
    3: <PreCheck />,
    4: <Install />,
    5: <ExitPage />,
  };

  useEffect(() => {
    getClusterList();
  }, []);

  return (
    <PageContainer
      style={{
        paddingBottom: 90,
        backgroundColor: '#f5f8ff',
        minHeight: '100vh',
      }}
    >
      <Steps
        currentStep={current}
        stepsItems={COMPONENT_INSTALL}
        showStepsKeys={STEPS_KEYS_COMP_INSTALL}
      />
      <div
        style={{
          paddingTop: `${current !== 6 ? 150 : 0}px`,
          width: '1040px',
          margin: '0 auto',
          overflow: 'auto',
        }}
      >
        {STEP_CONFIG[current]}
      </div>
    </PageContainer>
  );
}
