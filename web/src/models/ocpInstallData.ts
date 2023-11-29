import { useState } from 'react';
import type { TableDataType } from '@/component/DeployConfig/constants';
import {
  OCPComponent,
  OBComponent,
  OBProxyComponent,
} from '@/component/DeployConfig/constants';
import { getTailPath } from '@/utils/helper';

type VersionInfoType = {
  version: string;
  md5: string;
  release: string;
  versionType: 'ce' | 'business'; // Community Edition | Business version
  value?: string;
};

export type ConnectInfoType = {
  host?: string;
  port?: number;
  database?: string;
  accessUser?: string;
  accessCode?: string;
  user?: string;
  password?: string;
};
export default () => {
  const taiPath = getTailPath();
  const isNewDB = taiPath === 'install';
  const defaultTableData = isNewDB
    ? [OCPComponent, OBComponent, OBProxyComponent]
    : [OCPComponent];
  const [obVersionInfo, setObVersionInfo] = useState<VersionInfoType>();
  const [ocpVersionInfo, setOcpVersionInfo] = useState<VersionInfoType>();
  const [obproxyVersionInfo, setObproxyVersionInfo] =
    useState<VersionInfoType>();
  const [deployMemory, setDeployMemory] = useState(0);
  const [useRunningUser, setUseRunningUser] = useState<boolean>(false);
  const [checkConnectInfo, setCheckConnectInfo] = useState<
    'unchecked' | 'fail' | 'success'
  >('unchecked');
  const [installTaskId, setInstallTaskId] = useState<number>();
  const [installStatus, setInstallStatus] = useState<string>('RUNNING');
  const [installResult, setInstallResult] = useState<
    'SUCCESSFUL' | 'FAILED' | 'RUNNING'
  >();
  const [connectId, setConnectId] = useState<number>();
  const [isReinstall, setIsReinstall] = useState<boolean>(false);
  const [isSingleOcpNode, setIsSingleOcpNode] = useState<boolean>(); //undefined表示没有输入
  const [username, setUsername] = useState<string>('');
  const [logData, setLogData] = useState<API.InstallLog>({});
  const [isShowMoreConfig, setIsShowMoreConfig] = useState<boolean>(false);
  const [connectInfo, setConnectInfo] = useState<ConnectInfoType>();
  const [tableData, setTableData] = useState<TableDataType[]>(defaultTableData);
  return {
    obVersionInfo,
    setObVersionInfo,
    ocpVersionInfo,
    setOcpVersionInfo,
    obproxyVersionInfo,
    setObproxyVersionInfo,
    deployMemory,
    setDeployMemory,
    useRunningUser,
    setUseRunningUser,
    checkConnectInfo,
    setCheckConnectInfo,
    connectId,
    setConnectId,
    installTaskId,
    setInstallTaskId,
    installStatus,
    setInstallStatus,
    installResult,
    setInstallResult,
    isReinstall,
    setIsReinstall,
    isSingleOcpNode,
    setIsSingleOcpNode,
    username,
    setUsername,
    logData,
    setLogData,
    isShowMoreConfig,
    setIsShowMoreConfig,
    connectInfo,
    setConnectInfo,
    tableData,
    setTableData,
  };
};
