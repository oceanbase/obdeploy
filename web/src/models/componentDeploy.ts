import { useState } from 'react';
export type SelectedCluster = {
  name: string;
  ob_version: string;
  create_date: string;
  deploy_user: string;
  ob_servers: string[];
};

export default () => {
  const [current, setCurrent] = useState(1);
  const [preCheckInfoOk, setPreCheckInfoOk] = useState(false);
  const [installFinished, setInstallFinished] = useState(false);
  const [componentConfig, setComponentConfig] = useState<any>({});
  const [selectedConfig, setSelectedConfig] = useState<string[]>([]); // component_name
  const [deployUser, setDeployUser] = useState<string>('');
  const [componentsMore, setComponentsMore] = useState<boolean>(false);
  const [lowVersion, setLowVersion] = useState(false);
  const [componentsMoreConfig, setComponentsMoreConfig] = useState<
    API.NewParameterMeta[]
  >([]);
  const [selectedCluster, setSelectedCluster] = useState<SelectedCluster>();
  const [installStatus, setInstallStatus] = useState('RUNNING');
  const [deployedComps, setDeployedComps] = useState<string[]>([]);
  return {
    current,
    setCurrent,
    preCheckInfoOk,
    setPreCheckInfoOk,
    installFinished,
    setInstallFinished,
    componentConfig,
    setComponentConfig,
    selectedConfig,
    setSelectedConfig,
    deployUser,
    setDeployUser,
    componentsMore,
    lowVersion,
    setLowVersion,
    setComponentsMore,
    componentsMoreConfig,
    setComponentsMoreConfig,
    selectedCluster,
    setSelectedCluster,
    installStatus,
    setInstallStatus,
    deployedComps,
    setDeployedComps,
  };
};
