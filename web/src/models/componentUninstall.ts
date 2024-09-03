import { useState } from 'react';
import type { SelectedCluster } from './componentDeploy';
export type SelectedComponent = {
  component_name:string;
  version:string;
  node:string; // 多个解节点以 , 分开
}

export default () => {
  const [current, setCurrent] = useState(1);
  const [selectedCluster, setSelectedCluster] = useState<SelectedCluster>();
  const [selectedComponents, setSelectedComponents] = useState<SelectedComponent[]>([]); 
  return {
    current,
    setCurrent,
    selectedCluster,
    setSelectedCluster,
    selectedComponents,
    setSelectedComponents,
  };
};
