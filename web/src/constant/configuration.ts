import { intl } from '@/utils/intl';
export const NEW_METADB_OCP_INSTALL = [
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.DeploymentConfiguration',
      defaultMessage: '部署配置',
    }),
    key: 1,
  },
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.MetadbConfiguration',
      defaultMessage: 'MetaDB 配置',
    }),
    key: 2,
  },
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.OcpConfiguration',
      defaultMessage: 'OCP 配置',
    }),
    key: 3,
  },
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.PreCheck',
      defaultMessage: '预检查',
    }),
    key: 4,
  },
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.Deployment',
      defaultMessage: '部署',
    }),
    key: 5,
  },
];

export const METADB_OCP_INSTALL = [
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.DeploymentConfiguration',
      defaultMessage: '部署配置',
    }),
    key: 1,
  },
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.ObClusterConnectionConfiguration',
      defaultMessage: 'OB集群 连接配置',
    }),
    key: 2,
  },
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.OcpConfiguration',
      defaultMessage: 'OCP 配置',
    }),
    key: 3,
  },
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.PreCheck',
      defaultMessage: '预检查',
    }),
    key: 4,
  },
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.Deployment',
      defaultMessage: '部署',
    }),
    key: 5,
  },
];

export const COMPONENT_INSTALL = [
  {
    title: '部署配置',
    key: 1,
  },
  {
    title: '组件配置',
    key: 2,
  },
  {
    title: '预检查',
    key: 3,
  },
  {
    title: '部署',
    key: 4,
  },
];

export const COMPONENT_UNINSTALL = [
  {
    title: '卸载配置',
    key: 1,
  },
  {
    title: '卸载',
    key: 2,
  },
];

export const STEPS_KEYS_INSTALL = [1, 2, 3, 4, 5];
export const STEPS_KEYS_UPDATE = [1, 2, 3, 4];
export const STEPS_KEYS_COMP_INSTALL = [1, 2, 3, 4];
export const STEPS_KEYS_COMP_UNINSTALL = [1, 2];
export const METADB_OCP_UPDATE = [
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.DeploymentConfiguration',
      defaultMessage: '部署配置',
    }),
    key: 1,
  },
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.ConnectivityTest',
      defaultMessage: '联通性测试',
    }),
    key: 2,
  },
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.EnvironmentPreCheck',
      defaultMessage: '环境预检查',
    }),
    key: 3,
  },
  {
    title: intl.formatMessage({
      id: 'OBD.src.constant.configuration.OcpUpgrade',
      defaultMessage: 'OCP升级',
    }),
    key: 4,
  },
];

// ocp install
export const CONFIG_KEYS = {
  oceanbase: ['cpu_count', 'memory_limit', 'data_file', 'log_file'],
  obproxy: ['cpu_count', 'memory_limit', 'data_file', 'log_file'],
  // obagent: ['home_path', 'monagent_http_port', 'mgragent_http_port'],
  // ocpexpress: ['home_path', 'port'],
};

export const selectOcpexpressConfig = [
  'ocp_meta_tenant_max_cpu',
  'ocp_meta_tenant_memory_size',
  'ocp_meta_tenant_log_disk_size',
];

export const showConfigKeys = {
  oceanbase: [
    'home_path',
    'mode',
    'root_password',
    'data_dir',
    'redo_dir',
    'mysql_port',
    'rpc_port',
    'scenario',
  ],

  obproxy: [
    'home_path',
    'listen_port',
    'prometheus_listen_port',
    'rpc_listen_port',
  ],
  obagent: ['home_path', 'monagent_http_port', 'mgragent_http_port'],
  ocpexpress: ['home_path', 'port'],
  obconfigserver: [
    'home_path',
    'listen_port',
    'server_ip',
    'log_localtime',
    'log_compress',
  ],
};

export const ocpAddonAfter = '/ocp';
export const obproxyAddonAfter = '/obproxy';
export const oceanbaseAddonAfter = '/oceanbase';

export const OBD_COMMAND = 'obd web';
export const OBD_COMMAND_UPGRADE = 'obd web upgrade';

// 参数类型
export const PARAMETER_TYPE = {
  number: 'Integer',
  numberLogogram: 'int',
  string: 'String',
  capacity: 'Capacity',
  capacityMB: 'CapacityMB',
  boolean: 'Boolean',
};
