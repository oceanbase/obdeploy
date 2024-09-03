import CustomAlert from '@/component/CustomAlert';
import InstallResultComp, { ResultType } from '@/component/InstallResultComp';
import {
  componentChangeLog,
  componentChangeNodeCheck,
  componentChangeTask,
  getCommondConfigPath,
} from '@/services/component-change/componentChange';
import { getErrorInfo, handleQuit } from '@/utils';
import { connectInfoForPwd } from '@/utils/helper';
import { useModel } from '@umijs/max';
import { useRequest } from 'ahooks';
import { useEffect, useState } from 'react';
import { componentVersionTypeToComponent } from '../constants';

const getConnectInfo = (
  displayInfo: API.ComponentChangeInfoDisplay[] | undefined,
): API.ConnectionInfo[] | undefined => {
  if (!displayInfo) return;
  return displayInfo
    .filter(
      (info) =>
        info.access_string || info.address || info.password || info.username,
    )
    .map((item) => {
      return {
        component: item.component_name,
        access_url: item.address,
        user: item.username,
        password: item.password,
        connect_url: item.access_string,
      };
    });
};

const getReportInfo = (
  taskList: API.service_model_deployments_ComponentInfo[] | undefined,
  componentConfig: any,
): API.DeploymentReport[] => {
  if (!taskList || !componentConfig) return [];
  return taskList
    .filter(
      (task) =>
        componentConfig[
          componentVersionTypeToComponent[task.component] || task.component
        ],
    )
    .map((item) => ({
      name: item.component,
      version:
        componentConfig[
          componentVersionTypeToComponent[item.component] || item.component
        ].version,
      servers:
        componentConfig[
          componentVersionTypeToComponent[item.component] || item.component
        ].servers,
      status: item.result,
    }));
};

export default function InstallResult() {
  const {
    componentConfig,
    installStatus,
    setCurrent,
    selectedCluster,
    deployedComps,
  } = useModel('componentDeploy');
  const { setErrorVisible, setErrorsList, errorsList, handleQuitProgress } =
    useModel('global');
  const name = componentConfig?.appname;
  const [logs, setLogs] = useState({});
  const { run: getDisplayInfo, data: displayInfoRes } = useRequest(
    componentChangeNodeCheck,
    {
      manual: true,
    },
  );
  const { data: commondConfigPathRes, run: getConfigPath } = useRequest(
    getCommondConfigPath,
    {
      manual: true,
    },
  );
  const configPath = commondConfigPathRes?.data?.config_path;

  const { run: handleInstallLog, loading } = useRequest(componentChangeLog, {
    manual: true,
    onSuccess: (
      { success, data }: API.OBResponseInstallLog_,
      [{ components }]: [API.queryInstallLogParams],
    ) => {
      if (success) {
        setLogs({ ...logs, [components]: data?.log });
        setTimeout(() => {
          const log = document.getElementById(`report-log-${components}`);
          if (log) {
            log.scrollTop = log.scrollHeight;
          }
        });
      }
    },
    onError: (e: any) => {
      const errorInfo = getErrorInfo(e);
      setErrorVisible(true);
      setErrorsList([...errorsList, errorInfo]);
    },
  });
  const { data: componentChangeTaskRes } = useRequest(componentChangeTask, {
    defaultParams: [{ name }],
  });
  const ConfigserverAlert = () => (
    <CustomAlert
      type="info"
      showIcon={true}
      message={`obproxy 使用 obconfigserver 的相关功能，在执行 obd cluster restart ${selectedCluster?.name} -c obproxy-ce 重启 obproxy-ce 以后才能生效`}
    />
  );

  const exitOnOk = () => {
    handleQuit(handleQuitProgress, setCurrent, true, 5);
  };
  const taskList = componentChangeTaskRes?.data?.info;
  const displayInfo = displayInfoRes?.data;
  const connectInfo = connectInfoForPwd(
    getConnectInfo(displayInfo?.components_change_info) || [],
    componentConfig,
  );
  const reportInfo = getReportInfo(taskList, componentConfig);

  useEffect(() => {
    getDisplayInfo({ name });
    getConfigPath(name);
  }, []);
  return (
    <InstallResultComp
      installStatus={installStatus}
      name={name}
      handleInstallLog={handleInstallLog}
      loading={loading}
      logs={logs}
      type={ResultType.CompInstall}
      connectInfo={connectInfo}
      reportInfo={reportInfo}
      exitOnOk={exitOnOk}
      configPath={configPath}
      ConfigserverAlert={
        (deployedComps.includes('obproxy-ce') ||
          deployedComps.includes('obproxy')) &&
        connectInfo.some((item) => item.component === 'ob-configserver') ? (
          <ConfigserverAlert />
        ) : undefined
      }
    />
  );
}
