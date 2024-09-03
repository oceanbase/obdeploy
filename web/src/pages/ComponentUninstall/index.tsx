import Steps from '@/component/Steps';
import {
  COMPONENT_UNINSTALL,
  STEPS_KEYS_COMP_UNINSTALL,
} from '@/constant/configuration';
import { PageContainer } from '@ant-design/pro-components';
import { useModel } from '@umijs/max';

import ExitPage from '../Obdeploy/ExitPage';
import Uninstall from './Uninstall';
import UninstallConfig from './UninstallConfig';

export default function ComponentUninstall() {
  const { current } = useModel('componentUninstall');
  const STEP_CONFIG = {
    1: <UninstallConfig />,
    2: <Uninstall />,
    3: <ExitPage />,
  };
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
        stepsItems={COMPONENT_UNINSTALL}
        showStepsKeys={STEPS_KEYS_COMP_UNINSTALL}
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
