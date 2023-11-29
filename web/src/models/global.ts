import { useRef, useState } from 'react';
import useRequest from '@/utils/useRequest';
import { exitProcess } from '@/services/ob-deploy-web/Common';
import { queryDeploymentConfig } from '@/services/ob-deploy-web/Deployments';
import { getErrorInfo } from '@/utils';

//ocp reqestBody
// {
//   "auth": {
//     "user": "",
//     "password": "string",
//     "port": 22
//   },
//   "components": {
//     "oceanbase": {
//       "component": "string",
//       "appname": "string",
//       "version": "string",
//       "release": "string",
//       "package_hash": "",
//       "mode": "DEMO",
//       "root_password": "string",
//       "mysql_port": 0,
//       "rpc_port": 0,
//       "home_path": "",
//       "data_dir": "",
//       "redo_dir": "",
//       "parameters": [
//         {
//           "key": "string",
//           "value": "string",
//           "adaptive": true
//         }
//       ],
//       "topology": [
//         {
//           "name": "string",
//           "rootservice": "string",
//           "servers": [
//             {
//               "ip": "string",
//               "parameters": {}
//             }
//           ]
//         }
//       ]
//     },
//     "obproxy": {
//       "component": "string",
//       "version": "string",
//       "package_hash": "",
//       "release": "string",
//       "cluster_name": "string",
//       "home_path": "",
//       "prometheus_listen_port": 0,
//       "listen_port": 0,
//       "parameters": [
//         {
//           "key": "string",
//           "value": "string",
//           "adaptive": true
//         }
//       ],
//       "servers": [
//         "string"
//       ]
//     },
//     "ocpserver": {
//       "component": "ocp-server",
//       "version": "string",
//       "package_hash": "",
//       "release": "string",
//       "home_path": "",
//       "port": 0,
//       "admin_password": "string",
//       "parameters": [
//         {
//           "key": "string",
//           "value": "string",
//           "adaptive": true
//         }
//       ],
//       "memory_size": "2G",
//       "ocp_cpu": 0,
//       "meta_tenant": {
//         "name": {
//           "tenant_name": "string",
//           "user_name": "meta_user",
//           "user_database": "meta_database"
//         },
//         "password": "",
//         "resource": {
//           "cpu": 2,
//           "memory": 4
//         }
//       },
//       "monitor_tenant": {
//         "name": {
//           "tenant_name": "string",
//           "user_name": "meta_user",
//           "user_database": "meta_database"
//         },
//         "password": "",
//         "resource": {
//           "cpu": 2,
//           "memory": 4
//         }
//       },
//       "manage_info": {
//         "cluster": 0,
//         "tenant": 0,
//         "machine": 0
//       },
//       "servers": [
//         "string"
//       ],
//       "metadb": {
//         "id": 1,
//         "host": "string",
//         "port": 0,
//         "user": "string",
//         "password": "string",
//         "database": "oceanbase"
//       }
//     }
//   },
//   "home_path": "",
//   "launch_user": "string"
// }

export default () => {
  const initAppName = 'myoceanbase';
  const [selectedConfig, setSelectedConfig] = useState([
    'obproxy',
    'ocp-express',
    'obagent',
  ]); // 有ocpexpress必定有obagent
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [configData, setConfigData] = useState<any>({});
  const [ocpConfigData, setOcpConfigData] = useState<any>({});
  const [currentType, setCurrentType] = useState('all');
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
  const [token, setToken] = useState('');
  const [selectCluster, setSelectCluster] = useState<string>();
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
  const aliveTokenTimer = useRef<NodeJS.Timeout | null>(null)

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
    selectCluster,
    setSelectCluster
  };
};
