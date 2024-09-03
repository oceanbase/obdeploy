import { getDocs } from '@/constant/docs';
import { exitProcess } from '@/services/ob-deploy-web/Common';
import { queryDeploymentConfig } from '@/services/ob-deploy-web/Deployments';
import { getErrorInfo } from '@/utils';
import useRequest from '@/utils/useRequest';
import { getLocale } from '@umijs/max';
import { useRef, useState } from 'react';

export default () => {
  const initAppName = 'myoceanbase';

  let timerProgress: NodeJS.Timer | null = null;
  const [selectedConfig, setSelectedConfig] = useState([
    'obproxy',
    'ocp-express',
    'obagent',
  ]); // 有ocpexpress必定有obagent
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [configData, setConfigData] = useState<any>({});
  const [ocpConfigData, setOcpConfigData] = useState<any>({});
  const [checkOK, setCheckOK] = useState(false);
  const [installStatus, setInstallStatus] = useState('RUNNING');
  const [lowVersion, setLowVersion] = useState(false);
  const [isFirstTime, setIsFirstTime] = useState(true);
  const [ocpNewFirstTime, setOcpNewFirstTime] = useState(true);
  const [isDraft, setIsDraft] = useState(false);
  const [clusterMore, setClusterMore] = useState(false);
  const [ocpClusterMore, setOcpClusterMore] = useState(false);
  const [nameIndex, setNameIndex] = useState(4);
  const [ocpNameIndex, setOcpNameIndex] = useState(4);
  const [errorVisible, setErrorVisible] = useState(false);
  const [errorsList, setErrorsList] = useState<API.ErrorInfo[]>([]);
  const [first, setFirst] = useState<boolean>(true);
  const [loadTypeVisible, setLoadTypeVisible] = useState(false);
  const [token, setToken] = useState('');
  const [scenarioParam, setScenarioParam] = useState<any>();
  const [selectedLoadType, setSelectedLoadType] = useState('htap');
  const [clusterMoreConfig, setClusterMoreConfig] = useState<
    API.NewParameterMeta[]
  >([]);
  const [ocpClusterMoreConfig, setOcpClusterMoreConfig] = useState<
    API.NewParameterMeta[]
  >([]);
  const [proxyMoreConfig, setProxyMoreConfig] = useState<
    API.NewParameterMeta[]
  >([]);
  const [componentsMore, setComponentsMore] = useState(false);
  const [componentsMoreConfig, setComponentsMoreConfig] = useState<
    API.NewParameterMeta[]
  >([]);
  const [ocpCompMoreConfig, setOcpCompMoreConfig] = useState<
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
  const aliveTokenTimer = useRef<NodeJS.Timeout | null>(null);
  const docs = getDocs(getLocale);
  return {
    selectedConfig,
    setSelectedConfig,
    initAppName,
    currentStep,
    setCurrentStep,
    configData,
    setConfigData,
    ocpConfigData,
    setOcpConfigData,
    checkOK,
    setCheckOK,
    installStatus,
    setInstallStatus,
    lowVersion,
    setLowVersion,
    isFirstTime,
    setIsFirstTime,
    ocpNewFirstTime,
    setOcpNewFirstTime,
    isDraft,
    setIsDraft,
    clusterMore,
    scenarioParam,
    setScenarioParam,
    setClusterMore,
    ocpClusterMore,
    setOcpClusterMore,
    componentsMore,
    setComponentsMore,
    clusterMoreConfig,
    setClusterMoreConfig,
    ocpClusterMoreConfig,
    setOcpClusterMoreConfig,
    proxyMoreConfig,
    setProxyMoreConfig,
    componentsMoreConfig,
    setComponentsMoreConfig,
    ocpCompMoreConfig,
    setOcpCompMoreConfig,
    componentsVersionInfo,
    setComponentsVersionInfo,
    handleQuitProgress,
    getInfoByName,
    nameIndex,
    setNameIndex,
    ocpNameIndex,
    setOcpNameIndex,
    errorVisible,
    setErrorVisible,
    errorsList,
    setErrorsList,
    first,
    setFirst,
    token,
    setToken,
    aliveTokenTimer,
    loadTypeVisible,
    setLoadTypeVisible,
    selectedLoadType,
    setSelectedLoadType,
    timerProgress,
    ...docs,
  };
};
