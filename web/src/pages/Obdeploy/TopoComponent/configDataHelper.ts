import { intl } from '@/utils/intl';

/**
 * 从 configData 构建拓扑图数据
 */
export interface ConfigTopoNode {
  id: string;
  label: string;
  type: 'dns' | 'vip' | 'obproxy' | 'cluster' | 'zone';
  children?: ConfigTopoNode[];
  // DNS 节点
  domain?: string;
  // VIP 节点
  vipAddress?: string;
  vipPort?: number;
  // OBProxy 节点
  servers?: string[];
  // Cluster 节点
  clusterName?: string;
  // Zone 节点
  zoneName?: string;
  zoneIp?: string;
}

/**
 * 从服务器数组中提取 IP 地址
 * servers 可能是对象数组（有 ip 属性）或字符串数组
 */
const extractServerIps = (servers: any[]): string[] => {
  if (!Array.isArray(servers) || servers.length === 0) {
    return [];
  }
  
  return servers.map((server) => {
    if (typeof server === 'string') {
      return server;
    }
    if (server && typeof server === 'object' && server.ip) {
      return server.ip;
    }
    return '';
  }).filter(Boolean);
};

export const buildTopoDataFromConfig = (
  configData: API.DeploymentConfig,
): ConfigTopoNode | null => {
  if (!configData?.components) {
    return null;
  }

  const { oceanbase = {}, obproxy = {} } = configData.components;
  
  // 获取集群名称
  const clusterName = (oceanbase as any)?.appname || 'myoceanbase';
  
  // 获取 VIP 配置
  const vipAddress = (obproxy as any)?.vip_address;
  const vipPort = (obproxy as any)?.vip_port || (obproxy as any)?.listen_port || 2883;
  
  // 获取域名（从 obproxy.dns 获取）
  const domain = (obproxy as any)?.dns;
  
  // 获取 OBProxy 服务器列表（字符串数组）
  const obproxyServersRaw = (obproxy as any)?.servers || [];
  const obproxyServers = extractServerIps(obproxyServersRaw);
  
  // 获取 OceanBase topology（Zone 列表）
  const topology = (oceanbase as any)?.topology || [];
  
  // 如果没有 topology 数据，返回 null
  if (!Array.isArray(topology) || topology.length === 0) {
    return null;
  }

  // 构建 Zone 节点
  const zoneNodes: ConfigTopoNode[] = topology.map((zone: any, index: number) => {
    // 获取 Zone 的服务器列表
    const zoneServers = zone.servers || [];
    // 获取 Zone 的第一个服务器 IP（用于显示）
    const zoneIp = zoneServers.map((server: any) => server.ip).join(',');
    // 获取 Zone 名称
    const zoneName = zone.name || `Zone ${index + 1}`;

    return {
      id: `zone-${zone.name || index}`,
      label: zoneName,
      type: 'zone',
      zoneName,
      zoneIp,
    };
  });

  // 如果没有 Zone 节点，返回 null
  if (zoneNodes.length === 0) {
    return null;
  }

  // 构建 OceanBase 集群节点
  const clusterNode: ConfigTopoNode = {
    id: 'cluster',
    label: intl.formatMessage({
      id: 'OBD.pages.components.TopoComponent.OceanBaseCluster',
      defaultMessage: 'OceanBase 集群',
    }),
    type: 'cluster',
    clusterName,
    children: zoneNodes,
  };

  // 构建 OBProxy 节点
  // 如果 OBProxy 服务器列表为空，使用默认值（仅用于展示）
  const obproxyNode: ConfigTopoNode = {
    id: 'obproxy',
    label: 'OBProxy',
    type: 'obproxy',
    servers: obproxyServers.length > 0 
      ? obproxyServers 
      : (topology.length > 0 ? ['127.0.0.1', '127.0.0.2', '127.0.0.3'] : []),
    children: [clusterNode],
  };

  // 判断是否有 VIP 或 DNS
  const hasVip = vipAddress && vipAddress.trim();
  const hasDns = domain && domain.trim();

  // 如果存在 VIP，构建 VIP 节点
  if (hasVip) {
    const vipNode: ConfigTopoNode = {
      id: 'vip',
      label: 'VIP',
      type: 'vip',
      vipAddress,
      vipPort,
      children: [obproxyNode],
    };
    return vipNode;
  }

  // 如果存在 DNS，构建 DNS 节点
  if (hasDns) {
    const dnsNode: ConfigTopoNode = {
      id: 'dns',
      label: 'DNS',
      type: 'dns',
      domain, // 从 obproxy.dns 获取域名
      children: [obproxyNode],
    };
    return dnsNode;
  }

  // 如果既没有 VIP 也没有 DNS，直接返回 OBProxy 节点
  return obproxyNode;
};

