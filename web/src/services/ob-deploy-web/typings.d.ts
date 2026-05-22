declare namespace API {
  type Auth = {
    /** User ssh user */
    user?: string;
    /** Password ssh password */
    password?: string;
    /** Port ssh port */
    port?: number;
  };

  type backupOmsParams = {
    /** backup path */
    backup_path: string;
    /** backup pre check */
    pre_check?: boolean;
  };

  type BestComponentInfo = {
    /** Component Name component name, eq obporxy, ocp-express... */
    component_name: string;
    /** Version component version */
    version?: string;
    /** Deployed 0 - not deployed, 1 - deployed */
    deployed: number;
    /** Node component node */
    node?: string;
    /** Component Info component info */
    component_info?: service_model_components_ComponentInfo[];
  };

  type BodyCheckInfluxConnect = {
    /** Host host */
    host: string;
    /** Port port */
    port?: number;
    /** User user */
    user: string;
    /** Password password */
    password: string;
  };

  type BodyTakeoverOms = {
    /** Host oms container host */
    host: string;
    /** Container Name oms container name */
    container_name: string;
    /** User ssh user */
    user: string;
    /** Password ssh password */
    password: string;
    /** Port ssh port */
    port?: number;
  };

  type ClusterManageInfo = {
    /** Machine manage machine num */
    machine?: number;
  };

  type Component = {
    /** Name component name */
    name: string;
    /** Info info */
    info?: service_model_components_ComponentInfo[];
  };

  type ComponentChangeConfig = {
    /** Mode component change mode. eq 'scale_out', 'component_add' */
    mode: string;
    obproxy?: Obproxy;
    obagent?: Obagent;
    obconfigserver?: Obconfigserver;
    alertmanager?: service_model_componentChange_Alertmanager;
    grafana?: service_model_componentChange_Grafana;
    prometheus?: service_model_componentChange_Prometheus;
    ocpexpress?: service_model_componentChange_OcpExpress;
    /** Home Path component change config path */
    home_path: string;
  };

  type ComponentChangeConfigParams = {
    /** name */
    name: string;
  };

  type ComponentChangeDelComponentParams = {
    /** deployment name */
    name: string;
    /** component name */
    components: string[];
    /** force */
    force: boolean;
  };

  type ComponentChangeDelComponentTaskParams = {
    /** deployment name */
    name: string;
    /** offset to read task log */
    offset?: number;
    /** component name */
    components: string[];
  };

  type ComponentChangeDeploymentsInfoParams = {
    /** query deployment name */
    name: any;
  };

  type ComponentChangeDeploymentsInfoParams = {
    /** query deployment name */
    name: any;
  };

  type ComponentChangeInfo = {
    /** Component List component list */
    component_list: BestComponentInfo[];
  };

  type ComponentChangeInfoDisplay = {
    /** Component Name component name */
    component_name: string;
    /** Address url address */
    address?: string;
    /** Username username */
    username?: string;
    /** Password password */
    password?: string;
    /** Access String access string */
    access_string?: string;
  };

  type ComponentChangeLogParams = {
    /** deployment name */
    name: string;
    /** offset to read task log */
    offset?: number;
    /** component name */
    components?: string[];
  };

  type ComponentChangeMode = {
    /** Mode component change mode. eq 'scale_out', 'component_add' */
    mode: string;
  };

  type ComponentChangeNodeCheckParams = {
    /** deployment name */
    name: string;
  };

  type ComponentChangeNodeCheckParams = {
    /** deployment name */
    name: string;
    /** component name */
    components: string[];
  };

  type ComponentChangeParams = {
    /** deployment name */
    name: string;
  };

  type ComponentChangeTaskParams = {
    /** deployment name */
    name: string;
  };

  type ComponentChangeTaskParams = {
    /** deployment name */
    name: string;
  };

  type ComponentConfig = {
    oceanbase?: OceanBase;
    seekdb?: Seekdb;
    obproxy?: ObProxy;
    ocpexpress?: service_model_deployments_OcpExpress;
    obagent?: ObAgent;
    obclient?: ObClient;
    obconfigserver?: ObConfigserver;
    prometheus?: service_model_deployments_Prometheus;
    grafana?: service_model_deployments_Grafana;
    alertmanager?: service_model_deployments_Alertmanager;
  };

  type ComponentDepends = {
    /** Component Name component name */
    component_name: string;
    /** Depends depends component name */
    depends?: string[];
  };

  type ComponentsChangeInfoDisplay = {
    /** Components Change Info components change info */
    components_change_info: ComponentChangeInfoDisplay[];
  };

  type ComponentServer = {
    /** Component Name component name */
    component_name: string;
    /** Failed Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    failed_servers: string[];
  };

  type ComponentsServer = {
    /** Components Server components server */
    components_server: ComponentServer[];
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
  };

  type ConfigPath = {
    /** Config Path config path */
    config_path: string;
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

  type createMetadbConnectionParams = {
    /** whether the incoming tenant is the sys tenant */
    sys?: boolean;
  };

  type createOcpDeploymentConfigParams = {
    /** name */
    name: string;
  };

  type createOcpDeploymentParams = {
    /** cluster name */
    name: string;
  };

  type createOmsDeploymentConfigParams = {
    /** name */
    name: string;
  };

  type CreateTenantConfig = {
    /** Tenant Name tenant name */
    tenant_name?: string;
    /** Max Cpu max_cpu num */
    max_cpu?: number;
    /** Min Cpu min_cpu num */
    min_cpu?: number;
    /** Memory Size memory size */
    memory_size?: string;
    /** Log Disk Size log disk size */
    log_disk_size?: string;
    /** Mode tenant mode. {mysql, oracle} */
    mode: string;
    /** Charset database charset */
    charset: string;
    /** Variables Set the variables for the system tenant. [ob_tcp_invited_nodes='%']. */
    variables: string;
    /** Time Zone Tenant time zone. The default tenant time_zone is [+08:00]. */
    time_zone: string;
    /** Collate Tenant collate. */
    collate: string;
    /** Optimize Specify scenario optimization when creating a tenant, the default is consistent with the cluster dimension.
{express_oltp, complex_oltp, olap, htap, kv} */
    optimize?: string;
    /** Password When creating a tenant, set password for user. */
    password: string;
  };

  type createTenantParams = {
    name: string;
  };

  type createTenantTaskInfoParams = {
    /** create tenant task id */
    task_id: number;
  };

  type DatabaseConnection = {
    /** Cluster Name cluster name of the connection in installer */
    cluster_name?: string;
    /** Host host */
    host?: string;
    /** Port port */
    port?: number;
    /** User user */
    user?: string;
    /** Password password */
    password?: string;
    /** Database database */
    database?: string;
  };

  type DataListComponent_ = {
    /** Total */
    total?: number;
    /** Items */
    items?: Component[];
  };

  type DataListComponentDepends_ = {
    /** Total */
    total?: number;
    /** Items */
    items?: ComponentDepends[];
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

  type DataListDeployName_ = {
    /** Total */
    total?: number;
    /** Items */
    items?: DeployName[];
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

  type DataListScenarioType_ = {
    /** Total */
    total?: number;
    /** Items */
    items?: ScenarioType[];
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
    status: service_common_task_TaskResult;
  };

  type DeploymentStatus = 'INSTALLING' | 'DRAFT';

  type DeployMode = 'DEMO' | 'PRODUCTION';

  type DeployName = {
    /** Name deploy name list */
    name?: string;
    /** Deploy User deploy user */
    deploy_user?: string;
    /** Ob Servers ob servers */
    ob_servers?: string[];
    /** Ob Version ob version */
    ob_version?: string;
    /** Create Date ob create date */
    create_date?: string;
  };

  type DeployNames = {
    /** Name deploy name list */
    name?: string[];
  };

  type destroyDeploymentParams = {
    name: string;
  };

  type destroyOcpParams = {
    id: number;
  };

  type destroyOmsParams = {
    id: number;
  };

  type GetConfigPathParams = {
    /** deployment name */
    name: string;
  };

  type getConnectionInfoParams = {
    /** cluster name */
    name: string;
  };

  type getDeploymentParams = {
    /** task status,ex:INSTALLING,DRAFT */
    task_status: DeploymentStatus;
  };

  type getDestroyTaskInfoParams = {
    name: string;
  };

  type getInstalledOcpInfoParams = {
    /** deployment id */
    id: number;
  };

  type getMetadbConnectionParams = {
    /** cluster name */
    cluster_name: string;
  };

  type getOcpDestroyTaskParams = {
    /** deployment id */
    id: number;
    /** task id */
    task_id: number;
  };

  type getOcpInfoParams = {
    /** ocp cluster_name */
    cluster_name: string;
  };

  type getOcpInstallTaskLogParams = {
    /** deployment id */
    id: number;
    /** task id */
    task_id: number;
    /** offset to read task log */
    offset?: number;
  };

  type getOcpInstallTaskParams = {
    /** deployment id */
    id: number;
    /** task id */
    task_id: number;
  };

  type getOcpReinstallTaskLogParams = {
    /** deployment id */
    id: number;
    /** task id */
    task_id: number;
    /** offset to read task log */
    offset?: number;
  };

  type getOcpReinstallTaskParams = {
    /** deployment id */
    id: number;
    /** task id */
    task_id: number;
  };

  type getOcpUpgradePrecheckTaskParams = {
    /** ocp cluster_name */
    cluster_name: string;
    /** task id */
    task_id: number;
  };

  type getOcpUpgradeTaskLogParams = {
    /** ocp cluster_name */
    cluster_name: string;
    /** task id */
    task_id: number;
    /** offset to read task log */
    offset?: number;
  };

  type getOcpUpgradeTaskParams = {
    /** ocp cluster_name */
    cluster_name: string;
    /** task id */
    task_id: number;
  };

  type getOmsDestroyTaskParams = {
    /** deployment id */
    id: number;
    /** task id */
    task_id: number;
  };

  type getOmsInstallTaskLogParams = {
    /** deployment id */
    id: number;
    /** task id */
    task_id: number;
    /** offset to read task log */
    offset?: number;
  };

  type getOmsInstallTaskParams = {
    /** deployment id */
    id: number;
    /** task id */
    task_id: number;
  };

  type getOmsReinstallTaskLogParams = {
    /** deployment id */
    id: number;
    /** task id */
    task_id: number;
    /** offset to read task log */
    offset?: number;
  };

  type getOmsReinstallTaskParams = {
    /** deployment id */
    id: number;
    /** task id */
    task_id: number;
  };

  type getOmsUpgradePrecheckTaskParams = {
    /** oms cluster_name */
    cluster_name: string;
    /** task id */
    task_id: number;
  };

  type getOmsUpgradeTaskLogParams = {
    /** oms cluster_name */
    cluster_name: string;
    /** task id */
    task_id: number;
    /** offset to read task log */
    offset?: number;
  };

  type getOmsUpgradeTaskParams = {
    /** oms cluster_name */
    cluster_name: string;
    /** task id */
    task_id: number;
  };

  type getScenarioParams = {
    /** ob version */
    version?: string;
  };

  type getTelemetryDataParams = {
    /** deploy_name */
    name: string;
  };

  type getTenantScenarioParams = {
    name: string;
  };

  type getUpgradeInfoParams = {
    /** name */
    name: string;
  };

  type getUsableOmsDockerImagesParams = {
    /** oms servers */
    oms_servers: string;
    /** ssh username */
    username: string;
    /** ssh password */
    password: string;
    /** ssh port */
    port: number;
  };

  type HTTPValidationError = {
    /** Detail */
    detail?: ValidationError[];
  };

  type InstallLog = {
    /** Log install log */
    log?: string;
    /** Offset log offset */
    offset?: number;
  };

  type installOcpParams = {
    /** deployment id */
    id: number;
  };

  type installOmsParams = {
    /** deployment id */
    id: number;
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
    gpgcheck?: string | number;
    /** Enabled remote mirror is enabled */
    enabled?: boolean;
    /** Available remote mirror is enabled */
    available?: boolean;
  };

  type Obagent = {
    /** Component obagent component name, ex:obagent */
    component: string;
    /** Version version */
    version: string;
    /** Package Hash obagent package md5 */
    package_hash?: string;
    /** Release obagent release no */
    release: string;
    /** Monagent Http Port server port */
    monagent_http_port: number;
    /** Mgragent Http Port debug port */
    mgragent_http_port: number;
    /** Http Basic Auth Password http_basic_auth_password */
    http_basic_auth_password?: string;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
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

  type Obconfigserver = {
    /** Component component name */
    component: string;
    /** Version version */
    version: string;
    /** Package Hash package md5 */
    package_hash?: string;
    /** Release release no */
    release: string;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
    /** Listen Port server port */
    listen_port: number;
  };

  type ObConfigserver = {
    /** Component ob-configserver component name,ex:ob-configserver */
    component?: string;
    /** Version version */
    version: string;
    /** Release ob-configserver release no */
    release: string;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Home Path install ob-configserver home path */
    home_path?: string;
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
    /** Listen Port server port */
    listen_port: number;
  };

  type Obproxy = {
    /** Component obproxy component name, ex:obproxy-ce,obproxy */
    component: string;
    /** Version version */
    version: string;
    /** Package Hash obproxy package md5 */
    package_hash?: string;
    /** Release obproxy release no */
    release: string;
    /** Prometheus Listen Port prometheus port */
    prometheus_listen_port: number;
    /** Listen Port sql port */
    listen_port: number;
    /** Rpc Listen Port rpc port */
    rpc_listen_port?: number;
    /** Obproxy Sys Password obproxy_sys_password */
    obproxy_sys_password?: string;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
    /** Cluster Name cluster name */
    cluster_name?: string;
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
    /** Rpc Listen Port rpc service port */
    rpc_listen_port?: number;
    /** Listen Port sql port */
    listen_port: number;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
    /** Vip Address obproxy servers vip address */
    vip_address?: string;
    /** Vip Port obproxy servers vip port */
    vip_port?: string;
    /** Dns obproxy servers dns */
    dns?: string;
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

  type OBResponseComponentChangeInfo_ = {
    /** Code */
    code?: number;
    data?: ComponentChangeInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseComponentsChangeInfoDisplay_ = {
    /** Code */
    code?: number;
    data?: ComponentsChangeInfoDisplay;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseComponentsServer_ = {
    /** Code */
    code?: number;
    data?: ComponentsServer;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseConfigPath_ = {
    /** Code */
    code?: number;
    data?: ConfigPath;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseDatabaseConnection_ = {
    /** Code */
    code?: number;
    data?: DatabaseConnection;
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

  type OBResponseDataListComponentDepends_ = {
    /** Code */
    code?: number;
    data?: DataListComponentDepends_;
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

  type OBResponseDataListDeployName_ = {
    /** Code */
    code?: number;
    data?: DataListDeployName_;
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

  type OBResponseDataListScenarioType_ = {
    /** Code */
    code?: number;
    data?: DataListScenarioType_;
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

  type OBResponseDeployNames_ = {
    /** Code */
    code?: number;
    data?: DeployNames;
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

  type OBResponseOcpInfo_ = {
    /** Code */
    code?: number;
    data?: OcpInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseOcpInstalledInfo_ = {
    /** Code */
    code?: number;
    data?: OcpInstalledInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseOcpServerInfo_ = {
    /** Code */
    code?: number;
    data?: OcpServerInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseOcpUpgradeLostAddress_ = {
    /** Code */
    code?: number;
    data?: OcpUpgradeLostAddress;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponsePreCheckResult_ = {
    /** Code */
    code?: number;
    data?: service_model_deployments_PreCheckResult;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponsePrecheckTaskInfo_ = {
    /** Code */
    code?: number;
    data?: PrecheckTaskInfo;
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

  type OBResponseTaskLog_ = {
    /** Code */
    code?: number;
    data?: TaskLog;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OBResponseUserInfo_ = {
    /** Code */
    code?: number;
    data?: UserInfo;
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
    /** Obshell Port obshell port */
    obshell_port: number;
  };

  type OceanbaseServers = {
    /** Ip server ip */
    ip: string;
    /** Parameters */
    parameters?: Record<string, any>;
  };

  type OcpComponentConfig = {
    oceanbase?: OceanBase;
    obproxy?: ObProxy;
    ocpserver: OcpServer;
  };

  type OCPDeploymentStatus = 'INIT' | 'DEPLOYING' | 'FINISHED';

  type OCPDeploymnetConfig = {
    auth: Auth;
    components: OcpComponentConfig;
    /** Home Path global home path */
    home_path?: string;
    /** Launch User process user */
    launch_user?: string;
  };

  type OcpInfo = {
    /** Cluster Name ocp deployment cluster_name */
    cluster_name?: string;
    /** ocp deployment status, ex:INIT, FINISHED */
    status?: OCPDeploymentStatus;
    /** Current Version current ocp version */
    current_version: string;
    /** Ocp Servers ocp servers */
    ocp_servers: string[];
    /** Agent Servers servers deployed agent */
    agent_servers?: string[];
  };

  type OcpInstalledInfo = {
    /** Url Access address, eq: ip:port */
    url: string[];
    /** Account account */
    account?: string;
    /** Password account password */
    password: string;
  };

  type OcpServer = {
    /** Component ocp-server component name */
    component?: string;
    /** Version version */
    version?: string;
    /** Package Hash ocp-server package md5 */
    package_hash?: string;
    /** Release ocp-server release no */
    release?: string;
    /** Home Path install ocp-server home path */
    home_path?: string;
    /** Soft Dir software path */
    soft_dir?: string;
    /** Log Dir log dir */
    log_dir?: string;
    /** Ocp Site Url ocp server url */
    ocp_site_url?: string;
    /** Port server port */
    port: number;
    /** Admin Password admin password */
    admin_password: string;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Memory Size ocp server memory size */
    memory_size?: string;
    /** Ocp Cpu ocp server cpu num */
    ocp_cpu?: number;
    /** Meta Tenant meta tenant config */
    meta_tenant?: TenantConfig;
    /** Monitor Tenant monitor tenant config */
    monitor_tenant?: TenantConfig;
    /** Manage Info manage cluster info */
    manage_info?: ClusterManageInfo;
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
    /** Metadb connection info of metadb */
    metadb?: DatabaseConnection;
  };

  type OcpServerInfo = {
    /** User deploy user */
    user?: string;
    /** Ocp Version ocp-server current version */
    ocp_version?: string;
    /** Component component info */
    component?: service_model_server_ComponentInfo[];
    /** Tips display tips */
    tips?: boolean;
    /** Msg failed message */
    msg?: string;
  };

  type OcpUpgradeLostAddress = {
    /** Address lost ip address */
    address?: string[];
  };

  type OmsDeploymentConfig = {
    /** Auth ssh auth info */
    auth: SshAuth;
    /** Image image name */
    image: string;
    /** Servers oms nodes ips */
    servers: string;
    /** Mount Path oms mount path */
    mount_path: string;
    /** Drc Cm Db cm db name */
    drc_cm_db?: string;
    /** Drc Rm Db cm db name */
    drc_rm_db?: string;
    /** Oms Meta Host meta db host */
    oms_meta_host: string;
    /** Oms Meta Port meta db port */
    oms_meta_port?: number;
    /** Oms Meta User user */
    oms_meta_user?: string;
    /** Oms Meta Password meta db password */
    oms_meta_password?: string;
    /** Tsdb Password influxdb password */
    tsdb_password?: string;
    /** Tsdb Service influxdb service */
    tsdb_service?: string;
    /** Tsdb Url influxdb url */
    tsdb_url?: string;
    /** Tsdb Username influxdb username */
    tsdb_username?: string;
    /** Apsara Audit Sls Access Key sls key */
    apsara_audit_sls_access_key?: string;
    /** Apsara Audit Sls Access Secret sls secret */
    apsara_audit_sls_access_secret?: string;
    /** Apsara Audit Sls Endpoint sls endpoint */
    apsara_audit_sls_endpoint?: string;
    /** Apsara Audit Sls Ops Site Topic sls ops site topic */
    apsara_audit_sls_ops_site_topic?: string;
    /** Apsara Audit Sls User Site Topic sls user site topic */
    apsara_audit_sls_user_site_topic?: string;
    /** Ghana Server Port ghana server port */
    ghana_server_port?: number;
    /** Nginx Server Port nginx server port */
    nginx_server_port?: number;
    /** Cm Server Port cm server port */
    cm_server_port?: number;
    /** Supervisor Server Port supervisor server port */
    supervisor_server_port?: number;
    /** Sshd Server Port sshd server port */
    sshd_server_port?: number;
    /** Regions regions */
    regions: any[];
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

  type PrecheckComponentChangeParams = {
    /** deployment name */
    name: string;
  };

  type PrecheckComponentChangeResParams = {
    /** deployment name */
    name: string;
  };

  type PrecheckEventResult = 'PASSED' | 'FAILED' | 'RUNNING';

  type PreCheckInfo = {
    /** Name pre check item */
    name: string;
    /** Server server node */
    server: string;
    /** status, ex:FINISHED, RUNNING, PENDING */
    status?: service_common_task_TaskStatus;
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

  type precheckOcpDeploymentParams = {
    /** deployment id */
    id: number;
  };

  type precheckOcpParams = {
    /** deployment id */
    id: number;
    /** task id */
    task_id: number;
  };

  type precheckOcpUpgradeParams = {
    /** deployment cluster_name */
    cluster_name: string;
  };

  type precheckOmsDeploymentParams = {
    /** deployment id */
    id: number;
  };

  type precheckOmsParams = {
    /** deployment id */
    id: number;
    /** task id */
    task_id: number;
  };

  type precheckOmsUpgradeParams = {
    /** deployment cluster_name */
    cluster_name: string;
    /** oms upgrade default_oms_files_path */
    default_oms_files_path: string;
  };

  type preCheckParams = {
    name: string;
  };

  type preCheckStatusParams = {
    /** deployment name */
    name: string;
  };

  type PrecheckTaskInfo = {
    /** Task Info task detailed info */
    task_info?: service_model_task_TaskInfo;
    /** Precheck Result precheck result */
    precheck_result?: service_model_task_PreCheckResult[];
  };

  type PrecheckTaskResult = 'PASSED' | 'FAILED' | 'RUNNING';

  type queryComponentByComponentNameParams = {
    /** component name */
    component: string;
  };

  type queryConnectionInfoParams = {
    /** deployment name */
    name: string;
  };

  type queryCreateTenantLogParams = {
    /** create tenant task id */
    task_id: number;
    /** log offset */
    offset?: number;
    /** detail log */
    detail_log?: boolean;
  };

  type queryDeploymentConfigParams = {
    /** deployment name */
    name: string;
  };

  type queryDeploymentDetailParams = {
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

  type queryStartLogParams = {
    /** deployment name */
    name: string;
    /** log offset */
    offset?: number;
    /** component name */
    component_name?: string;
  };

  type queryStartStatusParams = {
    /** deployment name */
    name: string;
  };

  type queryStopLogParams = {
    /** deployment name */
    name: string;
    /** log offset */
    offset?: number;
    /** component name */
    component_name?: string;
  };

  type queryStopStatusParams = {
    /** deployment name */
    name: string;
  };

  type RecoverAdvisement = {
    /** Description advisement description */
    description?: string;
  };

  type RecoverComponentChangeParams = {
    /** deployment name */
    name: string;
  };

  type recoverOcpDeploymentParams = {
    /** deployment id */
    id: number;
  };

  type recoverParams = {
    /** deployment name */
    name: string;
  };

  type reinstallOcpParams = {
    /** deployment id */
    id: number;
  };

  type reinstallOmsParams = {
    /** deployment id */
    id: number;
  };

  type RemoveComponentParams = {
    /** deployment name */
    name: string;
    /** component name List */
    components: string[];
  };

  type ScenarioType = {
    /** Type scenario name */
    type: string;
    /** Desc scenario description */
    desc: string;
    /** Value scenario value */
    value: string;
  };

  type Seekdb = {
    /** Component seekdb */
    component: string;
    /** Version SeekDB package version / tag from mirror */
    version?: string;
    /** Servers Server IPs, e.g. ['192.168.1.10'] */
    servers: string[];
    /** Home Path SeekDB working directory; empty uses global home_path/seekdb */
    home_path?: string;
    /** Data Dir Data directory */
    data_dir: string;
    /** Redo Dir Redo / clog directory */
    redo_dir: string;
    /** Mysql Port MySQL protocol port */
    mysql_port?: number;
    /** Obshell Port OBShell port */
    obshell_port?: number;
    /** Parameters config parameter */
    parameters?: Parameter[];
  };

  type service_api_v1_deployments_DataListRecoverChangeParameter = {
    /** Total */
    total?: number;
    /** Items */
    items?: service_model_deployments_RecoverChangeParameter[];
  };

  type service_api_v1_deployments_OBResponseDataListRecoverChangeParameter = {
    /** Code */
    code?: number;
    data?: service_api_v1_deployments_DataListRecoverChangeParameter;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type service_api_v1_deployments_OBResponseTaskInfo = {
    /** Code */
    code?: number;
    data?: service_model_deployments_TaskInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type service_api_v1_ocpDeployments_DataListRecoverChangeParameter = {
    /** Total */
    total?: number;
    /** Items */
    items?: service_model_metadb_RecoverChangeParameter[];
  };

  type service_api_v1_ocpDeployments_OBResponseDataListRecoverChangeParameter = {
    /** Code */
    code?: number;
    data?: service_api_v1_ocpDeployments_DataListRecoverChangeParameter;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type service_api_v1_omsDeployments_OBResponseTaskInfo = {
    /** Code */
    code?: number;
    data?: service_model_task_TaskInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type service_common_task_TaskResult = 'SUCCESSFUL' | 'FAILED' | 'RUNNING';

  type service_common_task_TaskStatus = 'PENDING' | 'RUNNING' | 'FINISHED';

  type service_model_componentChange_Alertmanager = {
    /** Component component name */
    component: string;
    /** Version version */
    version: string;
    /** Package Hash package md5 */
    package_hash?: string;
    /** Release release no */
    release: string;
    /** Port server port */
    port: number;
    /** Basic Auth Users user and password */
    basic_auth_users?: Record<string, any>;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
  };

  type service_model_componentChange_Grafana = {
    /** Component component name */
    component: string;
    /** Version version */
    version: string;
    /** Package Hash package md5 */
    package_hash?: string;
    /** Release release no */
    release: string;
    /** Port server port */
    port: number;
    /** Login Password user and password */
    login_password?: string;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
  };

  type service_model_componentChange_OcpExpress = {
    /** Component component name */
    component: string;
    /** Version version */
    version: string;
    /** Package Hash package md5 */
    package_hash?: string;
    /** Release release no */
    release: string;
    /** Port server port */
    port: number;
    /** Admin Passwd admin password */
    admin_passwd?: string;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
  };

  type service_model_componentChange_Prometheus = {
    /** Component component name */
    component: string;
    /** Version version */
    version: string;
    /** Package Hash package md5 */
    package_hash?: string;
    /** Release release no */
    release: string;
    /** Port server port */
    port: number;
    /** Basic Auth Users user and password */
    basic_auth_users?: Record<string, any>;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
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

  type service_model_deployments_Alertmanager = {
    /** Component alertmanager component name,ex:alertmanager */
    component?: string;
    /** Version version */
    version: string;
    /** Release alertmanager release no */
    release: string;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Home Path install alertmanager home path */
    home_path?: string;
    /** Servers server ip, ex:[ '1.1.1.1'] */
    servers: string[];
    /** Port server port */
    port: number;
    /** Basic Auth Users auth user and password */
    basic_auth_users: Record<string, any>;
  };

  type service_model_deployments_ComponentInfo = {
    /** Component install component name */
    component: string;
    /** status, ex:FINISHED, RUNNING, PENDING */
    status: service_common_task_TaskStatus;
    /** result, ex:SUCCESSFUL, FAILED */
    result: service_common_task_TaskResult;
  };

  type service_model_deployments_Grafana = {
    /** Component grafana component name,ex:prometheus */
    component?: string;
    /** Version version */
    version: string;
    /** Release grafana release no */
    release: string;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Home Path install grafana home path */
    home_path?: string;
    /** Servers server ip, ex:[ '1.1.1.1'] */
    servers: string[];
    /** Port server port */
    port: number;
    /** Login Password login password */
    login_password: string;
  };

  type service_model_deployments_OcpExpress = {
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
    /** Admin Passwd ocp-express admin password */
    admin_passwd: string;
  };

  type service_model_deployments_PreCheckResult = {
    /** Total total item for pre check */
    total?: number;
    /** Finished finished item for pre check */
    finished?: number;
    /** All Passed is all passed */
    all_passed?: boolean;
    /** pre check task status,ex:RUNNING,SUCCESSFUL,FAILED */
    status?: service_common_task_TaskResult;
    /** Message pre check task message */
    message?: string;
    /** Info pre check item info */
    info?: PreCheckInfo[];
  };

  type service_model_deployments_Prometheus = {
    /** Component prometheus component name,ex:prometheus */
    component?: string;
    /** Version version */
    version: string;
    /** Release prometheus release no */
    release: string;
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Home Path install prometheus home path */
    home_path?: string;
    /** Servers server ip, ex:[ '1.1.1.1'] */
    servers: string[];
    /** Port server port */
    port: number;
    /** Basic Auth Users auth user and password */
    basic_auth_users: Record<string, any>;
  };

  type service_model_deployments_RecoverChangeParameter = {
    /** Name repaired item */
    name: string;
    /** Old Value old value item */
    old_value?: any;
    /** New Value new value item */
    new_value?: any;
  };

  type service_model_deployments_TaskInfo = {
    /** Total total item for install */
    total?: number;
    /** Finished finished item for install */
    finished?: number;
    /** Current current item for install */
    current?: string;
    /** status,ex:RUNNING,SUCCESSFUL,FAILED */
    status: service_common_task_TaskResult;
    /** Msg task message */
    msg?: string;
    /** Info install item info */
    info?: service_model_deployments_ComponentInfo[];
  };

  type service_model_metadb_RecoverChangeParameter = {
    /** Name repaired item */
    name: string;
    /** Old Value old value item */
    old_value?: string;
    /** New Value new value item */
    new_value?: string;
  };

  type service_model_server_ComponentInfo = {
    /** Name ocp component */
    name?: string;
    /** Ip server address */
    ip?: string[];
  };

  type service_model_task_PreCheckResult = {
    /** Name precheck event name */
    name: string;
    /** Server precheck server */
    server?: string;
    /** precheck event result */
    result?: PrecheckEventResult;
    /** Recoverable precheck event recoverable */
    recoverable?: boolean;
    /** Code error code */
    code?: string;
    /** Description error description */
    description?: string;
    /** Advisement advisement of precheck event failure */
    advisement?: string;
  };

  type service_model_task_TaskInfo = {
    /** Id task id */
    id: number;
    /** task status */
    status: service_model_task_TaskStatus;
    /** task result */
    result: service_model_task_TaskResult;
    /** Total total steps */
    total?: string;
    /** Finished finished steps */
    finished?: string;
    /** Current current step */
    current?: string;
    /** Message task message */
    message?: string;
    /** Info */
    info?: TaskStepInfo[];
  };

  type service_model_task_TaskResult = 'SUCCESSFUL' | 'FAILED' | 'RUNNING';

  type service_model_task_TaskStatus = 'RUNNING' | 'FINISHED';

  type ServiceInfo = {
    /** User user name */
    user: string;
  };

  type SshAuth = {
    /** User username */
    user?: string;
    /** auth method */
    auth_method?: SshAuthMethod;
    /** Password password */
    password?: string;
    /** Private Key private key */
    private_key?: string;
    /** Port ssh port */
    port?: number;
  };

  type SshAuthMethod = 'PUBKEY' | 'PASSWORD';

  type startADeploymentParams = {
    name: string;
  };

  type stopADeploymentParams = {
    name: string;
  };

  type takeoverOmsParams = {
    /** oms cluster_name */
    cluster_name: string;
  };

  type TaskLog = {
    /** Log task log content */
    log?: string;
    /** Offset offset of current log */
    offset?: number;
  };

  type TaskStepInfo = {
    /** Name task step */
    name?: string;
    /** task step status */
    status?: service_model_task_TaskStatus;
    /** task step result */
    result?: service_model_task_TaskResult;
  };

  type TenantConfig = {
    /** Name tenant name */
    name: TenantUser;
    /** Password tenant password */
    password?: string;
    /** Resource tenant resource */
    resource?: TenantResource;
  };

  type TenantResource = {
    /** Cpu cpu resource of a tenant */
    cpu?: number;
    /** Memory memory resource of a tenant in GB */
    memory?: number;
  };

  type TenantUser = {
    /** Tenant Name tenant name */
    tenant_name: string;
    /** User Name user name */
    user_name?: string;
    /** User Database user database */
    user_database?: string;
  };

  type unitResourceParams = {
    name: string;
  };

  type upgradeOcpParams = {
    /** ocp cluster_name */
    cluster_name: string;
    /** ocp upgrade version */
    version: string;
    /** ocp upgrade hash */
    usable?: string;
  };

  type upgradeOmsParams = {
    /** oms cluster_name */
    cluster_name: string;
    /** oms upgrade version */
    version: string;
    /** oms upgrade image_name */
    image_name?: string;
    /** oms upgrade mode */
    upgrade_mode?: string;
  };

  type UserCheck = {
    /** User ssh user */
    user?: string;
    /** Password ssh password */
    password?: string;
    /** Port ssh port */
    port?: number;
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
  };

  type UserInfo = {
    /** Username system user */
    username: string;
  };

  type validateOrSetKeepAliveTokenParams = {
    /** token */
    token?: string;
    /** force set token when conflict */
    overwrite?: boolean;
    /** is need clear token */
    is_clear?: boolean;
  };

  type ValidationError = {
    /** Location */
    loc: (string | number)[];
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
