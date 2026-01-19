export type BasicInfoProp = {
  appname: string;
  type: string;
  productsInfo: ProductInfoType[];
};

export type ProductInfoType = {
  productName: string;
  version: string;
  isCommunity?: boolean;
};

export type DBNodeType = {
  id?: string;
  name: string;
  rootservice: string;
  servers: string[];
};

export type ConnectInfoType = { label: string; value: string }[];

export type ConnectInfoPropType = {
  userConfig: { user: string; password: string; port: number };
  ocpNodeConfig: string[];
  dbNode: DBNodeType[];
  clusterConfig: {
    info: {
      root_password: string;
      home_path: string;
      data_dir: string;
      redo_dir: string;
      mysql_port: number;
      rpc_port: number;
      obshell_port: number;
    };
    more?: any;
  };
  obproxyConfig: {
    info: {
      servers: string[];
      home_path: string;
      listen_port: number;
      prometheus_listen_port: number;
    };
    more?: any;
  };
};

export type ResourceInfoPropType = {
  userConfig?: { user: string; password: string; port: number };
  serviceConfig: {
    admin_password: string;
    home_path: string;
    log_dir: string;
    soft_dir: string;
    ocp_site_url: string;
  };
  resourcePlan: {
    cluster: number;
    tenant: number;
    machine: number;
  };
  memory_size: string;
  tenantConfig: {
    info: {
      tenant_name: string;
      password: string;
    };
    resource: { cpu: number; memory: number };
  };
  monitorConfig: {
    info: {
      tenant_name: string;
      password: string;
    };
    resource: { cpu: number; memory: number };
  };
  ocpServer?: string[];
};
