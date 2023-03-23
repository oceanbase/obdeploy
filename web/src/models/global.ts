import { useState } from 'react';
import useRequest from '@/utils/useRequest';
import { finishInstallAndKillProcess } from '@/services/ob-deploy-web/Processes';
import { queryDeploymentConfig } from '@/services/ob-deploy-web/Deployments';

export default () => {
  const initAppName = 'myoceanbase';
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [configData, setConfigData] = useState<any>({});
  const [currentType, setCurrentType] = useState('all');
  const [checkOK, setCheckOK] = useState(false);
  const [installStatus, setInstallStatus] = useState('RUNNING');
  const [lowVersion, setLowVersion] = useState(false);
  const [isFirstTime, setIsFirstTime] = useState(true);
  const [isDraft, setIsDraft] = useState(false);
  const [clusterMore, setClusterMore] = useState(false);
  const [nameIndex, setNameIndex] = useState(4);

  const [clusterMoreConfig, setClusterMoreConfig] = useState<
    API.NewParameterMeta[]
  >([]);
  const [componentsMore, setComponentsMore] = useState(false);
  const [componentsMoreConfig, setComponentsMoreConfig] = useState<
    API.NewParameterMeta[]
  >([]);
  const [componentsVersionInfo, setComponentsVersionInfo] =
    useState<API.ComponentsVersionInfo>({});

  const { run: handleQuitProgress } = useRequest(finishInstallAndKillProcess);
  const { run: getInfoByName } = useRequest(queryDeploymentConfig, {
    skipStatusError: true,
    throwOnError: true,
  });

  return {
    initAppName,
    currentStep,
    setCurrentStep,
    configData,
    setConfigData,
    currentType,
    setCurrentType,
    checkOK,
    setCheckOK,
    installStatus,
    setInstallStatus,
    lowVersion,
    setLowVersion,
    isFirstTime,
    setIsFirstTime,
    isDraft,
    setIsDraft,
    clusterMore,
    setClusterMore,
    componentsMore,
    setComponentsMore,
    clusterMoreConfig,
    setClusterMoreConfig,
    componentsMoreConfig,
    setComponentsMoreConfig,
    componentsVersionInfo,
    setComponentsVersionInfo,
    handleQuitProgress,
    getInfoByName,
    nameIndex,
    setNameIndex,
  };
};
