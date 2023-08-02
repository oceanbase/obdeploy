import { useState } from 'react';
import useRequest from '@/utils/useRequest';
import { exitProcess } from '@/services/ob-deploy-web/Common';
import { queryDeploymentConfig } from '@/services/ob-deploy-web/Deployments';
import { getErrorInfo } from '@/utils';

export default () => {
  const initAppName = 'myoceanbase';
  const [selectedConfig,setSelectedConfig] = useState(['obproxy','ocp-express','obagent']); // 有ocpexpress必定有obagent
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
  const [errorVisible, setErrorVisible] = useState(false);
  const [errorsList, setErrorsList] = useState<API.ErrorInfo[]>([]);

  const [clusterMoreConfig, setClusterMoreConfig] = useState<
    API.NewParameterMeta[]
  >([]);
  const [componentsMore, setComponentsMore] = useState(false);
  const [componentsMoreConfig, setComponentsMoreConfig] = useState<
    API.NewParameterMeta[]
  >([]);
  const [componentsVersionInfo, setComponentsVersionInfo] =
    useState<API.ComponentsVersionInfo>({});

  const { run: handleQuitProgress } = useRequest(exitProcess, {
    onError: (e: any) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });
  const { run: getInfoByName } = useRequest(queryDeploymentConfig, {
    throwOnError: true,
  });

  return {
    selectedConfig,
    setSelectedConfig,
    initAppName,
    currentStep,
    setCurrentStep,
    configData,
    setConfigData,
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
    errorVisible,
    setErrorVisible,
    errorsList,
    setErrorsList,
  };
};
