/* eslint-disable */
// 该文件由 OneAPI 自动生成，请勿手动修改！

declare namespace API {
  interface ComponentInfo {
    /** Name ocp component */
    name?: string;
    /** Ip server address */
    ip?: string;
  }

  interface DataList_DatabaseConnection_ {
    /** Total */
    total?: number;
    /** Items */
    items?: Array<DatabaseConnection>;
  }

  interface DataList_MetaDBResource_ {
    /** Total */
    total?: number;
    /** Items */
    items?: Array<MetaDBResource>;
  }

  interface DataList_MetadbDeploymentInfo_ {
    /** Total */
    total?: number;
    /** Items */
    items?: Array<MetadbDeploymentInfo>;
  }

  interface DataList_OcpDeploymentInfo_ {
    /** Total */
    total?: number;
    /** Items */
    items?: Array<OcpDeploymentInfo>;
  }

  interface DataList_RecoverChangeParameter_ {
    /** Total */
    total?: number;
    /** Items */
    items?: Array<RecoverChangeParameter>;
  }

  interface DataList_ResourceCheckResult_ {
    /** Total */
    total?: number;
    /** Items */
    items?: Array<ResourceCheckResult>;
  }

  interface DatabaseConnection {
    /** Id id of the connection in installer */
    id?: number;
    /** Host host */
    host: string;
    /** Port port */
    port: number;
    /** User user */
    user: string;
    /** Password password */
    password: string;
    /** Database database */
    database?: string;
    cluster_name?: string;
  }

  type DeploymentStatus = 'INIT' | 'DEPLOYING' | 'FINISHED';

  interface Disk {
    /** Path path */
    path: string;
    /** Disk Info disk info */
    disk_info: any;
  }

  interface DiskInfo {
    /** Dev dev */
    dev: string;
    /** Mount Path mount path */
    mount_path: string;
    /** Total Size total size */
    total_size: string;
    /** Free Size free size */
    free_size: string;
  }

  interface HTTPValidationError {
    /** Detail */
    detail?: Array<ValidationError>;
  }

  type InstallerMode = 'STANDARD' | 'COMPACT';

  interface MetaDBResource {
    /** Address server address */
    address: string;
    /** Disk path: disk_info */
    disk: Array<Disk>;
    /** Memory Limit Lower Limit memory_limit lower limit */
    memory_limit_lower_limit: number;
    /** Memory Limit Higher Limit memory_limit higher limit */
    memory_limit_higher_limit: number;
    /** Memory Limit Default default memory_limit */
    memory_limit_default: number;
    /** Data Size Default default data size */
    data_size_default: number;
    /** Log Size Default default log size */
    log_size_default: number;
    /** Flag which solution to use */
    flag: number;
  }

  interface MetadbDeploymentConfig {
    /** Auth ssh auth info */
    auth?: any;
    /** Cluster Name cluster name */
    cluster_name?: string;
    /** Servers servers to deploy */
    servers: Array<string>;
    /** Root Password password of user root@sys */
    root_password?: string;
    /** Home Path home path to install */
    home_path?: string;
    /** Data Dir data directory */
    data_dir?: string;
    /** Log Dir log directory */
    log_dir?: string;
    /** Sql Port sql port */
    sql_port?: number;
    /** Rpc Port rpc port */
    rpc_port?: number;
    /** Devname devname */
    devname?: string;
    /** Parameters config parameter */
    parameters?: Array<Parameter>;
  }

  interface MetadbDeploymentInfo {
    /** Id metadb deployment id */
    id?: number;
    /** metadb deployment status, ex: INIT, FINISHED */
    status?: any;
    /** Config metadb deployment */
    config?: any;
    /** Connection connection info of metadb */
    connection?: any;
  }

  interface MetadbResource {
    /** Servers observer resource */
    servers: Array<ObserverResource>;
  }

  interface OBResponse {
    /** Code */
    code?: number;
    /** Data */
    data?: any;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_DataList_DatabaseConnection__ {
    /** Code */
    code?: number;
    data?: DataList_DatabaseConnection_;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_DataList_MetaDBResource__ {
    /** Code */
    code?: number;
    data?: DataList_MetaDBResource_;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_DataList_MetadbDeploymentInfo__ {
    /** Code */
    code?: number;
    data?: DataList_MetadbDeploymentInfo_;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_DataList_OcpDeploymentInfo__ {
    /** Code */
    code?: number;
    data?: DataList_OcpDeploymentInfo_;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_DataList_RecoverChangeParameter__ {
    /** Code */
    code?: number;
    data?: DataList_RecoverChangeParameter_;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_DataList_ResourceCheckResult__ {
    /** Code */
    code?: number;
    data?: DataList_ResourceCheckResult_;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_DatabaseConnection_ {
    /** Code */
    code?: number;
    data?: DatabaseConnection;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_MetadbDeploymentInfo_ {
    /** Code */
    code?: number;
    data?: MetadbDeploymentInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_OperatingUser_ {
    /** Code */
    code?: number;
    data?: string;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_OcpDeploymentInfo_ {
    /** Code */
    code?: number;
    data?: OcpDeploymentInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_OcpInfo_ {
    /** Code */
    code?: number;
    data?: OcpInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface connectMetaDB_ {
    /** Code */
    code?: number;
    data?: connectMetaDB;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface createUpgradePrecheck_ {
    /** Code */
    code?: number;
    data?: string;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_OcpInstalledInfo_ {
    /** Code */
    code?: number;
    data?: OcpInstalledInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_OcpResource_ {
    /** Code */
    code?: number;
    data?: OcpResource;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_OcpUpgradeLostAddress_ {
    /** Code */
    code?: number;
    data?: OcpUpgradeLostAddress;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface ClusterNames_ {
    /** Code */
    code?: number;
    data?: ClusterNames;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface ConnectInfo_ {
    /** Code */
    code?: number;
    data?: ConnectInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_PrecheckTaskInfo_ {
    /** Code */
    code?: number;
    data?: PrecheckTaskInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_ServerInfo_ {
    /** Code */
    code?: number;
    data?: ServerInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_TaskInfo_ {
    /** Code */
    code?: number;
    data?: TaskInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_TaskLog_ {
    /** Code */
    code?: number;
    data?: TaskLog;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface OBResponse_UserInfo_ {
    /** Code */
    code?: number;
    data?: UserInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  }

  interface ObserverResource {
    /** Address observer address */
    address: string;
    /** Cpu Total total cpu */
    cpu_total: number;
    /** Cpu Free free cpu */
    cpu_free: number;
    /** Memory Total total memory size */
    memory_total: number;
    /** Memory Free free memory size */
    memory_free: number;
  }

  interface OcpDeploymentConfig {
    /** Auth ssh auth info */
    auth?: any;
    /** Metadb connection info of metadb */
    metadb: any;
    /** Meta Tenant meta tenant config */
    meta_tenant?: any;
    /** Monitor Tenant monitor tenant config */
    monitor_tenant?: any;
    /** Appname ocp app name */
    appname?: string;
    /** Admin Password ocp login password */
    admin_password: string;
    /** Servers servers to deploy */
    servers: Array<string>;
    /** Home Path home path to install */
    home_path?: string;
    /** Server Port server port */
    server_port?: number;
    /** Parameters */
    parameters?: Array<Parameter>;
  }

  interface OcpDeploymentInfo {
    /** Id metadb deployment id */
    id?: number;
    /** ocp deployment status, ex: INIT, DEPLOYING, FINISHED */
    status?: any;
    /** Config ocp deployment config */
    config: any;
    /** Monitor Display monitor tenant configured */
    monitor_display?: boolean;
  }

  interface OcpInfo {
    /** Id ocp deployment id */
    id?: number;
    /** ocp deployment status, ex:INIT, FINISHED */
    status?: any;
    /** Current Version current ocp version */
    current_version: string;
    /** Ocp Servers ocp servers */
    ocp_servers: Array<string>;
    /** Agent Servers servers deployed agent */
    agent_servers?: Array<string>;
  }

  interface connectMetaDB {
    ocp_version: string;
    component: any[];
    tips: boolean;
    msg: string;
    user:string;
  }

  interface OcpInstalledInfo {
    /** Url Access address, eq: ip:port */
    url: Array<string>;
    /** Account account */
    account?: string;
    /** Password account password */
    password: string;
  }

  interface OcpResource {
    /** Servers server resource */
    servers: Array<ServerResource>;
    /** Metadb metadb resource */
    metadb: any;
  }

  interface OcpUpgradeLostAddress {
    /** Address lost ip address */
    address?: Array<string>;
  }

  interface ClusterNames {
    name: string[];
  }
  interface ConnectInfo {
    host: string;
    port: number;
    user: string;
    password: string;
    database: string;
    cluster_name: string;
  }

  interface Parameter {
    /** Name parameter name */
    name: string;
    /** Value parameter value */
    value: string;
  }

  interface PreCheckResult {
    /** Name precheck event name */
    name: string;
    /** Server precheck server */
    server?: string;
    /** precheck event result */
    result?: any;
    /** Recoverable precheck event recoverable */
    recoverable?: boolean;
    /** Code error code */
    code?: string;
    /** Advisement advisement of precheck event failure */
    advisement?: string;
  }

  type PrecheckEventResult = 'PASSED' | 'FAILED' | 'RUNNING';

  interface PrecheckTaskInfo {
    /** Task Info task detailed info */
    task_info?: any;
    /** Precheck Result precheck result */
    precheck_result?: Array<PreCheckResult>;
  }

  interface RecoverChangeParameter {
    /** Name repaired item */
    name: string;
    /** Old Value old value item */
    old_value?: string;
    /** New Value new value item */
    new_value?: string;
  }

  interface ResourceCheckResult {
    /** Address server ip */
    address: string;
    /** Name path */
    name: string;
    /** Check Result check result, true/false */
    check_result?: boolean;
    /** Error Message error message, eq path not enough */
    error_message?: Array<string>;
  }

  interface ServerInfo {
    /** User username */
    user?: string;
    /** Ocp Version ocp version with installer */
    ocp_version?: string;
    /** Component component info */
    component?: Array<ComponentInfo>;
    /** server mode,ex:standard,compact */
    mode?: any;
    metadb?: DatabaseConnection;
    /** Msg failed message */
    msg?: string;
    /** Status eq: 0, 1 */
    status?: number;
  }

  interface ServerResource {
    /** Address server address */
    address: string;
    /** Cpu Total total cpu */
    cpu_total: number;
    /** Cpu Free free cpu */
    cpu_free: number;
    /** Memory Total total memory size */
    memory_total: string;
    /** Memory Free free memory size */
    memory_free: string;
    /** Disk disk info */
    disk: Array<DiskInfo>;
  }

  interface SshAuth {
    /** User username */
    user?: string;
    /** auth method */
    auth_method?: any;
    /** Password password */
    password?: string;
    /** Private Key private key */
    private_key?: string;
    /** Port ssh port */
    port?: number;
  }

  type SshAuthMethod = 'PUBKEY' | 'PASSWORD';

  interface TaskInfo {
    /** Id task id */
    id: number;
    /** task status */
    status: any;
    /** task result */
    result: any;
    /** Total total steps */
    total?: string;
    /** Finished finished steps */
    finished?: string;
    /** Current current step */
    current?: string;
    /** Message task message */
    message?: string;
    /** Info */
    info?: Array<TaskStepInfo>;
  }

  interface TaskLog {
    /** Log task log content */
    log?: string;
    /** Offset offset of current log */
    offset?: number;
  }

  type TaskResult = 'SUCCESSFUL' | 'FAILED' | 'RUNNING';

  type TaskStatus = 'RUNNING' | 'FINISHED';

  interface TaskStepInfo {
    /** Name task step */
    name?: string;
    /** task step status */
    status?: any;
    /** task step result */
    result?: any;
  }

  interface TenantConfig {
    /** Name tenant name */
    name: any;
    /** Password root password of the tenant */
    password?: string;
    /** Resource tenant resource */
    resource?: any;
  }

  interface TenantResource {
    /** Cpu cpu resource of a tenant */
    cpu?: number;
    /** Memory memory resource of a tenant in GB */
    memory?: number;
  }

  interface TenantUser {
    /** Tenant Name tenant name */
    tenant_name: string;
    /** User Name user name */
    user_name?: string;
    /** User Database user database */
    user_database?: string;
  }

  interface UserInfo {
    /** Username system user */
    username: string;
  }

  interface ValidationError {
    /** Location */
    loc: Array<any>;
    /** Message */
    msg: string;
    /** Error Type */
    type: string;
  }

  interface OperatingUser {
    user: string;
    password: string;
    port: number;
    servers: string[];
  }
}
