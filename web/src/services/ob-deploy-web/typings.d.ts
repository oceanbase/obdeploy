declare namespace API {
  type Auth = {
    /** User ssh user */
    user?: string;
    /** Password ssh password */
    password?: string;
    /** Port ssh port */
    port?: number;
  };

  type Component = {
    /** Name component name */
    name: string;
    /** Info info */
    info?: service_model_components_ComponentInfo[];
  };

  type ComponentConfig = {
    oceanbase: OceanBase;
    obproxy?: ObProxy;
    ocpexpress?: OcpExpress;
    obagent?: ObAgent;
    obclient?: ObClient;
    ocpserver?: OcpServer;
  };

  type ConfigParameter = {
    /** Is Essential is essential */
    is_essential?: boolean;
    /** Name parameter name */
    name?: string;
    /** Require parameter is it required */
    require?: boolean;
    /** Auto parameter can be calculated automatically */
    auto?: boolean;
    /** Description parameter description */
    description?: string;
    /** Type parameter type */
    type?: string;
    /** Default parameter default value */
    default?: string;
    /** Min Value parameter min value */
    min_value?: string;
    /** Max Value parameter max value */
    max_value?: string;
    /** Need Redeploy need redeploy */
    need_redeploy?: boolean;
    /** Modify Limit modify limit */
    modify_limit?: string;
    /** Need Reload need reload */
    need_reload?: boolean;
    /** Need Restart need restart */
    need_restart?: boolean;
    /** Section section */
    section?: string;
    is_changed?: boolean;
  };

  type ConnectionInfo = {
    /** Component component name */
    component: string;
    /** Access Url access url */
    access_url: string;
    /** User user */
    user: string;
    /** Password password */
    password: string;
    /** Connect Url connect url */
    connect_url: string;
  };

  type createDeploymentConfigParams = {
    /** name */
    name: string;
  };

  type componentsDependsItems = {
    component_name: string;
    depends: string[];
  }[];

  type componentsDepends = {
    /** Total */
    total?: number;
    /** Items */
    items?: componentsDependsItems;
  };

  type DataListComponent_ = {
    /** Total */
    total?: number;
    /** Items */
    items?: Component[];
  };

  type DataListConnectionInfo_ = {
    /** Total */
    total?: number;
    /** Items */
    items?: ConnectionInfo[];
  };

  type DataListDeployment_ = {
    /** Total */
    total?: number;
    /** Items */
    items?: Deployment[];
  };

  type DataListDeploymentReport_ = {
    /** Total */
    total?: number;
    /** Items */
    items?: DeploymentReport[];
  };

  type DataListMirror_ = {
    /** Total */
    total?: number;
    /** Items */
    items?: Mirror[];
  };

  type DataListParameterMeta_ = {
    /** Total */
    total?: number;
    /** Items */
    items?: ParameterMeta[];
  };

  type DataListRecoverChangeParameter_ = {
    /** Total */
    total?: number;
    /** Items */
    items?: RecoverChangeParameter[];
  };

  type deployAndStartADeploymentParams = {
    name: string;
  };

  type Deployment = {
    /** Name deployment name */
    name: string;
    /** Status status, ex:CONFIGURED,DEPLOYED,STARTING,RUNNING,DESTROYED,UPGRADING */
    status: string;
  };

  type DeploymentConfig = {
    auth: Auth;
    components: ComponentConfig;
    /** Home Path global home path */
    home_path?: string;
  };

  type DeploymentInfo = {
    /** Name deployment name */
    name?: string;
    /** Config Path config path */
    config_path?: string;
    /** Status ex:CONFIGURING,CONFIGURED,DEPLOYING,DEPLOYED,RUNNING,STOPPING,STOPPED,DESTROYING,DESTROYED,UPGRADING */
    status?: string;
    config?: DeploymentConfig;
  };

  type DeploymentReport = {
    /** Name component name */
    name: string;
    /** Version component version */
    version: string;
    /** Servers server ip */
    servers: string[];
    /** status, ex: RUNNING, SUCCESSFUL, FAILED */
    status: TaskResult;
  };

  type DeploymentStatus = 'INSTALLING' | 'DRAFT';

  type DeployMode = 'DEMO' | 'PRODUCTION';

  type destroyDeploymentParams = {
    name: string;
  };

  type getDeploymentParams = {
    /** task status,ex:INSTALLING,DRAFT */
    task_status: DeploymentStatus;
  };

  type getDestroyTaskInfoParams = {
    name: string;
  };

  type HTTPValidationError = {
    /** Detail */
    detail?: ValidationError[];
  };

  type InstallLog = {
    total: number;
    items: {
      component_name: string;
      log: string;
    }[];
  };

  type Mirror = {
    /** Mirror Path mirror path */
    mirror_path?: string;
    /** Name mirror name */
    name: string;
    /** Section Name section name */
    section_name?: string;
    /** Baseurl baseurl */
    baseurl?: string;
    /** Repomd Age repomd age */
    repomd_age?: number;
    /** Repo Age repo age */
    repo_age?: number;
    /** Priority priority */
    priority?: number;
    /** Gpgcheck gpgcheck */
    gpgcheck?: string;
    /** Enabled remote mirror is enabled */
    enabled?: boolean;
    /** Available remote mirror is enabled */
    available?: boolean;
  };

  type ObAgent = {
    /** Component obagent component name,ex:obagent */
    component?: string;
    /** Version version */
    version: string;
    /** Package Hash obagent package md5 */
    package_hash?: string;
    /** Release obagent release no */
    release: string;
    /** Home Path install obagent home path */
    home_path?: string;
    /** Monagent Http Port server port */
    monagent_http_port: number;
    /** Mgragent Http Port debug port */
    mgragent_http_port: number;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
  };

  type ObClient = {
    /** Component obclient component name,ex:obclient */
    component?: string;
    /** Version version */
    version: string;
    /** Release obclient release no */
    release: string;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Home Path install obclient home path */
    home_path?: string;
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
  };

  type ObProxy = {
    /** Component obproxy component name, ex:obproxy-ce,obproxy */
    component: string;
    /** Version version */
    version: string;
    /** Package Hash obproxy package md5 */
    package_hash?: string;
    /** Release obproxy release no */
    release: string;
    /** Cluster Name obproxy name */
    cluster_name?: string;
    /** Home Path install obproxy home path */
    home_path?: string;
    /** Prometheus Listen Port prometheus port */
    prometheus_listen_port: number;
    /** Listen Port sql port */
    listen_port: number;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
  };

  type OBResponse = {
    /** Code */
    code?: number;
    /** Data */
    data?: any;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseComponent_ = {
    /** Code */
    code?: number;
    data?: Component;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type ComponentsDepends_ = {
    /** Code */
    code?: number;
    data?: componentsDepends;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type CommondConfigPath = {
    /** Code */
    code?: number;
    data?: { config_path: string };
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseDataListComponent_ = {
    /** Code */
    code?: number;
    data?: DataListComponent_;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseDataListConnectionInfo_ = {
    /** Code */
    code?: number;
    data?: DataListConnectionInfo_;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseDataListDeployment_ = {
    /** Code */
    code?: number;
    data?: DataListDeployment_;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseDataListDeploymentReport_ = {
    /** Code */
    code?: number;
    data?: DataListDeploymentReport_;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseDataListMirror_ = {
    /** Code */
    code?: number;
    data?: DataListMirror_;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseDataListParameterMeta_ = {
    /** Code */
    code?: number;
    data?: DataListParameterMeta_;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type ScenarioType = { type: string; desc: string; value: string };

  type OBResponseDataListScenarioType = {
    /** Code */
    code?: number;
    data?: {
      total: number;
      items: ScenarioType[];
    };
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseDataListRecoverChangeParameter_ = {
    /** Code */
    code?: number;
    data?: DataListRecoverChangeParameter_;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseDeploymentInfo_ = {
    /** Code */
    code?: number;
    data?: DeploymentInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseInstallLog_ = {
    /** Code */
    code?: number;
    data?: InstallLog;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponsePreCheckResult_ = {
    /** Code */
    code?: number;
    data?: PreCheckResult;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseServiceInfo_ = {
    /** Code */
    code?: number;
    data?: ServiceInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseTaskInfo_ = {
    /** Code */
    code?: number;
    data?: TaskInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OceanBase = {
    /** Component oceanbase component name,ex:oceanbase-ce,oceanbase */
    component: string;
    /** Appname cluster name */
    appname: string;
    /** Version version */
    version: string;
    /** Release oceanbase release no */
    release: string;
    /** Package Hash oceanbase package md5 */
    package_hash?: string;
    /** deploy mode ex:DEMO,PRODUCTION */
    mode: DeployMode;
    /** Root Password root password */
    root_password: string;
    /** Mysql Port sql port */
    mysql_port: number;
    /** Rpc Port rpc port */
    rpc_port: number;
    /** Home Path install OceanBase home path */
    home_path?: string;
    /** Data Dir OceanBase data path */
    data_dir?: string;
    /** Redo Dir clog path */
    redo_dir?: string;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Topology topology */
    topology: Zone[];
  };

  type OceanbaseServers = {
    /** Ip server ip */
    ip: string;
    /** Parameters */
    parameters?: Record<string, any>;
  };

  type OcpExpress = {
    /** Component ocp-express component name */
    component?: string;
    /** Version version */
    version: string;
    /** Package Hash ocp-express package md5 */
    package_hash?: string;
    /** Release ocp-express release no */
    release: string;
    /** Home Path install ocp-express home path */
    home_path?: string;
    /** Port server port */
    port: number;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
    /** Admin password */
    admin_passwd: string;
  };

  type OcpServer = {
    component: string;
    version: string;
    release: string;
    package_hash: string;
    servers: string[];
    admin_password: string;
    home_path: string;
    log_dir: string;
    soft_dir: string;
    ocp_site_url?: string | string[];
    port: number;
    manage_info: {
      machine: number;
    };
    memory_size: number;
    meta_tenant: {
      name: {
        tenant_name: string;
      };
      password: string;
      resource: {
        cpu: number;
        memory: number;
      };
    };
    monitor_tenant: {
      name: {
        tenant_name: string;
      };
      password: string;
      resource: {
        cpu: number;
        memory: number;
      };
    };
  };

  type Parameter = {
    /** Key parameter key */
    key: string;
    /** Value parameter value */
    value: string;
    /** Adaptive parameter value is adaptive */
    adaptive?: boolean;
  };

  type ParameterFilter = {
    /** Component component name */
    component: string;
    /** Version version name */
    version: string;
    /** Is Essential Only essential parameter filter */
    is_essential_only?: boolean;
  };

  type ParameterMeta = {
    /** Component */
    component: string;
    /** Version */
    version: string;
    /** Config Parameters */
    config_parameters: ConfigParameter[];
  };

  type ParameterRequest = {
    /** Filters parameter filters */
    filters: ParameterFilter[];
  };

  type PreCheckInfo = {
    /** Name pre check item */
    name: string;
    /** Server server node */
    server: string;
    /** status, ex:FINISHED, RUNNING, PENDING */
    status?: TaskStatus;
    /** result, ex:PASSED, FAILED */
    result?: PrecheckTaskResult;
    /** Recoverable can be automatically repaired */
    recoverable?: boolean;
    /** Code error code */
    code?: string;
    /** Description error description */
    description?: string;
    /** Advisement repaired suggestion */
    advisement?: RecoverAdvisement;
  };

  type preCheckParams = {
    name: string;
  };

  type PreCheckResult = {
    /** Total total item for pre check */
    total?: number;
    /** Finished finished item for pre check */
    finished?: number;
    /** All Passed is all passed */
    all_passed?: boolean;
    /** pre check task status,ex:RUNNING,SUCCESSFUL,FAILED */
    status?: TaskResult;
    /** Message pre check task message */
    message?: string;
    /** Info pre check item info */
    info?: PreCheckInfo[];
  };

  type preCheckStatusParams = {
    /** deployment name */
    name: string;
  };

  type PrecheckTaskResult = 'PASSED' | 'FAILED' | 'RUNNING';

  type queryComponentByComponentNameParams = {
    /** component name */
    component: string;
  };

  type queryComponentParametersParams = {
    'accept-language'?: string;
  };

  type queryConnectionInfoParams = {
    /** deployment name */
    name: string;
  };

  type queryDeploymentConfigParams = {
    /** deployment name */
    name: string;
  };

  type queryDeploymentReportParams = {
    /** deployment name */
    name: string;
  };

  type queryInstallLogParams = {
    /** deployment name */
    name: string;
    /** log offset */
    offset?: number;
    /** component name */
    component_name?: string;
  };

  type queryInstallStatusParams = {
    /** deployment name */
    name: string;
  };

  type RecoverAdvisement = {
    /** Description advisement description */
    description?: string;
  };

  type RecoverChangeParameter = {
    /** Name repaired item */
    name: string;
    /** Old Value old value item */
    old_value?: any;
    /** New Value new value item */
    new_value?: any;
  };

  type recoverParams = {
    /** deployment name */
    name: string;
  };

  type service_model_components_ComponentInfo = {
    /** Estimated Size estimated size after install */
    estimated_size?: number;
    /** Version component version */
    version?: string;
    /** Type component type,ex:remote,local */
    type?: string;
    /** Release component release no */
    release?: string;
    /** Arch component package arch info */
    arch?: string;
    /** Md5 component package md5 info */
    md5?: string;
    /** Version Type  version type,ex:ce,business */
    version_type?: string;
  };

  type service_model_deployments_ComponentInfo = {
    /** Component install component name */
    component: string;
    /** status, ex:FINISHED, RUNNING, PENDING */
    status: TaskStatus;
    /** result, ex:SUCCESSFUL, FAILED */
    result: TaskResult;
  };

  type ServiceInfo = {
    /** User user name */
    user: string;
  };

  type TaskInfo = {
    /** Total total item for install */
    total?: number;
    /** Finished finished item for install */
    finished?: number;
    /** Current current item for install */
    current?: string;
    /** status,ex:RUNNING,SUCCESSFUL,FAILED */
    status: TaskResult;
    /** Msg task message */
    msg?: string;
    /** Info install item info */
    info?: service_model_deployments_ComponentInfo[];
  };

  type TaskResult = 'SUCCESSFUL' | 'FAILED' | 'RUNNING';

  type TaskStatus = 'PENDING' | 'RUNNING' | 'FINISHED';

  type validateOrSetKeepAliveTokenParams = {
    /** token */
    token?: string;
    /** force set token when conflict */
    overwrite?: boolean;
  };

  type ValidationError = {
    /** Location */
    loc: any[];
    /** Message */
    msg: string;
    /** Error Type */
    type: string;
  };

  type Zone = {
    /** Name zone name */
    name: string;
    /** Rootservice root service */
    rootservice: string;
    /** Servers */
    servers: OceanbaseServers[];
  };
}
