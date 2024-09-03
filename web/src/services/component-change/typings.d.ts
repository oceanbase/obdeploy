declare namespace API {
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

  type ComponentChangeConfig = {
    /** Mode component change mode. eq 'scale_out', 'component_add' */
    mode: string;
    obproxy?: Obproxy;
    obagent?: Obagent;
    obconfigserver?: Obconfigserver;
    ocpexpress?: OcpExpress;
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
    component_name: string[];
    /** force */
    force: boolean;
  };

  type ComponentChangeDelComponentTaskParams = {
    /** deployment name */
    name: string;
    /** offset to read task log */
    offset?: number;
    /** component name */
    component_name: string[];
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
    component_name?: string;
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
    component_name: string[];
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

  type DataListDeployName_ = {
    /** Total */
    total?: number;
    /** Items */
    items?: DeployName[];
  };

  type DataListRecoverChangeParameter_ = {
    /** Total */
    total?: number;
    /** Items */
    items?: RecoverChangeParameter[];
  };

  type DeployName = {
    /** Name deploy name list */
    name?: string;
    /** Ob Version ob version */
    ob_version?: string;
    /** Create Date ob create date */
    create_date?: string;
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
    /** Parameters config parameter */
    parameters?: Parameter[];
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
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
    /** Cluster Name cluster name */
    cluster_name?: string;
    obproxy_sys_password?: string;
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

  type OBResponseDataListDeployName_ = {
    /** Code */
    code?: number;
    data?: DataListDeployName_;
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

  type OBResponseTaskInfo_ = {
    /** Code */
    code?: number;
    data?: TaskInfo;
    /** Msg */
    msg?: string;
    /** Success */
    success?: boolean;
  };

  type OcpExpress = {
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
    /** Parameters config parameter */
    parameters?: Parameter[];
    /** Servers server ip, ex:[ '1.1.1.1','2.2.2.2'] */
    servers: string[];
  };

  type Parameter = {
    /** Key parameter key */
    key: string;
    /** Value parameter value */
    value: string;
    /** Adaptive parameter value is adaptive */
    adaptive?: boolean;
  };

  type PrecheckComponentChangeParams = {
    /** deployment name */
    name: string;
  };

  type PrecheckComponentChangeResParams = {
    /** deployment name */
    name: string;
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

  type PrecheckTaskResult = 'PASSED' | 'FAILED' | 'RUNNING';

  type RecoverAdvisement = {
    /** Description advisement description */
    description?: string;
  };

  type RecoverChangeParameter = {
    /** Name repaired item */
    name: string;
    /** Old Value old value item */
    old_value?: string;
    /** New Value new value item */
    new_value?: string;
  };

  type RecoverComponentChangeParams = {
    /** deployment name */
    name: string;
  };

  type RemoveComponentParams = {
    /** deployment name */
    name: string;
    /** component name List */
    components: string[];
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

  type ValidationError = {
    /** Location */
    loc: (string | number)[];
    /** Message */
    msg: string;
    /** Error Type */
    type: string;
  };
}
