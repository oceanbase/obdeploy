/* eslint-disable */
// 该文件由 OneAPI 自动生成，请勿手动修改！
import { request } from 'umi';

/** get_installed_ocp_info get_installed_ocp_info GET /api/v1/ocp/info/${param0} */
export async function getInstalledOcpInfo(
  params: {
    // path
    /** deployment id */
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_OcpInstalledInfo_>(
    `/api/v1/ocp/info/${param0}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** list_ocp_deployments list ocp deployments GET /api/v1/ocp/deployments */
export async function listOcpDeployments(options?: { [key: string]: any }) {
  return request<API.OBResponse_DataList_OcpDeploymentInfo__>(
    '/api/v1/ocp/deployments',
    {
      method: 'GET',
      ...(options || {}),
    },
  );
}

/** create_ocp_deployment create deployment for ocp POST /api/v1/ocp/deployments */
export async function createOcpDeployment(
  body?: API.OcpDeploymentConfig,
  options?: { [key: string]: any },
) {
  return request<API.OBResponse_OcpDeploymentInfo_>('/api/v1/ocp/deployments', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  });
}

/** get_ocp_deployment get ocp deployment GET /api/v1/ocp/deployments/${param0} */
export async function getOcpDeployment(
  params: {
    // path
    /** deployment id */
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_OcpDeploymentInfo_>(
    `/api/v1/ocp/deployments/${param0}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** destroy_ocp destroy ocp DELETE /api/v1/ocp/deployments/${param0} */
export async function destroyOcp(
  params: {
    // path
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/ocp/deployments/${param0}`,
    {
      method: 'DELETE',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** get_ocp_deployment_resource get server resource for ocp deployment GET /api/v1/ocp/deployments/${param0}/resource */
export async function getOcpDeploymentResource(
  params: {
    // path
    /** deployment id */
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_OcpResource_>(
    `/api/v1/ocp/deployments/${param0}/resource`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

export async function createOcpDeploymentConfig(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.createDeploymentConfigParams,
  body: API.DeploymentConfig,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/ocp_deployments/${param0}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    params: { ...queryParams },
    data: body,
    ...(options || {}),
  });
}

export async function getTelemetryData(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.createDeploymentConfigParams,
  body: API.DeploymentConfig,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/telemetry/${param0}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    params: { ...queryParams },
    data: body,
    ...(options || {}),
  });
}
export async function telemetryReport(params: {}): Promise<any> {
  return fetch('https://openwebapi.oceanbase.com/api/web/oceanbase/report', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  }).then((response) => response.json());
}

/** precheck_ocp_deployment precheck for ocp deployment POST /api/v1/ocp/deployments/${param0}/precheck */
export async function precheckOcpDeployment(
  params: {
    // path
    /** deployment id */
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/ocp/deployments/${param0}/precheck`,
    {
      method: 'POST',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** precheck_ocp precheck for ocp deployment GET /api/v1/ocp/deployments/${param0}/precheck/${param1} */
export async function precheckOcp(
  params: {
    // path
    /** deployment id */
    id?: number;
    /** task id */
    task_id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1 } = params;
  return request<API.OBResponse_PrecheckTaskInfo_>(
    `/api/v1/ocp/deployments/${param0}/precheck/${param1}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** recover_ocp_deployment recover ocp deployment config POST /api/v1/ocp/deployments/${param0}/recover */
export async function recoverOcpDeployment(
  params: {
    // path
    /** deployment id */
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_DataList_RecoverChangeParameter__>(
    `/api/v1/ocp/deployments/${param0}/recover`,
    {
      method: 'POST',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** install_ocp install ocp POST /api/v1/ocp/deployments/${param0}/install */
export async function installOcp(
  params: {
    // path
    /** deployment id */
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/ocp/deployments/${param0}/install`,
    {
      method: 'POST',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** get_ocp_install_task get ocp install task GET /api/v1/ocp/deployments/${param0}/install/${param1} */
export async function getOcpInstallTask(
  params: {
    // path
    /** deployment id */
    id?: number;
    /** task id */
    task_id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/ocp/deployments/${param0}/install/${param1}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** get_ocp_install_task_log get ocp install task log GET /api/v1/ocp/deployments/${param0}/install/${param1}/log */
export async function getOcpInstallTaskLog(
  params: {
    // query
    /** offset to read task log */
    offset?: number;
    // path
    /** deployment id */
    id?: number;
    /** task id */
    task_id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponse_TaskLog_>(
    `/api/v1/ocp/deployments/${param0}/install/${param1}/log`,
    {
      method: 'GET',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** get_ocp_install_task_report get ocp install task report GET /api/v1/ocp/deployments/${param0}/install/${param1}/report */
export async function getOcpInstallTaskReport(
  params: {
    // query
    /** offset to read task log */
    offset?: number;
    // path
    /** deployment id */
    id?: number;
    /** task id */
    task_id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponse_TaskLog_>(
    `/api/v1/ocp/deployments/${param0}/install/${param1}/report`,
    {
      method: 'GET',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** reinstall_ocp reinstall ocp POST /api/v1/ocp/deployments/${param0}/reinstall */
export async function reinstallOcp(
  params: {
    // path
    /** deployment id */
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/ocp/deployments/${param0}/reinstall`,
    {
      method: 'POST',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** get_ocp_reinstall_task get ocp reinstall task GET /api/v1/ocp/deployments/${param0}/reinstall/${param1} */
export async function getOcpReinstallTask(
  params: {
    // path
    /** deployment id */
    id?: number;
    /** task id */
    task_id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/ocp/deployments/${param0}/reinstall/${param1}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** get_ocp_reinstall_task_log get ocp reinstall task log GET /api/v1/ocp/deployments/${param0}/reinstall/${param1}/log */
export async function getOcpReinstallTaskLog(
  params: {
    // query
    /** offset to read task log */
    offset?: number;
    // path
    /** deployment id */
    id?: number;
    /** task id */
    task_id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponse_TaskLog_>(
    `/api/v1/ocp/deployments/${param0}/reinstall/${param1}/log`,
    {
      method: 'GET',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** get_ocp_reinstall_task_report get ocp reinstall task report GET /api/v1/ocp/deployments/${param0}/reinstall/${param1}/report */
export async function getOcpReinstallTaskReport(
  params: {
    // query
    /** offset to read task log */
    offset?: number;
    // path
    /** deployment id */
    id?: number;
    /** task id */
    task_id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponse_TaskLog_>(
    `/api/v1/ocp/deployments/${param0}/reinstall/${param1}/report`,
    {
      method: 'GET',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** get_ocp_destroy_task get ocp destroy task GET /api/v1/ocp/deployments/${param0}/destroy/${param1} */
export async function getOcpDestroyTask(
  params: {
    // path
    /** deployment id */
    id?: number;
    /** task id */
    task_id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/ocp/deployments/${param0}/destroy/${param1}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** create_ocp_info create ocp info POST /api/v1/ocp */
export async function createOcpInfo(
  body?: API.DatabaseConnection,
  options?: { [key: string]: any },
) {
  return request<API.OBResponse_OcpInfo_>('/api/v1/ocp', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  });
}

/** get_ocp_info get ocp info GET /api/v1/ocp/${param0} */
export async function getOcpInfo(
  params: {
    // path
    /** ocp id */
    // id?: number;
    cluster_name?: string;
  },
  options?: { [key: string]: any },
) {
  const { cluster_name: param0 } = params;
  return request<API.OBResponse_OcpInfo_>(`/api/v1/ocp/${param0}`, {
    method: 'GET',
    params: { ...params },
    ...(options || {}),
  });
}

/** precheck_ocp_upgrade post precheck for ocp upgrade POST /api/v1/ocp/${param0}/upgrade/precheck */
export async function precheckOcpUpgrade(
  params: {
    // path
    /** deployment id */
    // id?: number;
    cluster_name?: string;
  },
  options?: { [key: string]: any },
) {
  const { cluster_name: param0 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/ocp/${param0}/upgrade/precheck`,
    {
      method: 'POST',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** get_ocp_upgrade_precheck_task get precheck for ocp upgrade GET /api/v1/ocp/${param0}/upgrade/precheck/${param1} */
export async function getOcpUpgradePrecheckTask(
  params: {
    // path
    /** ocp id */
    // id?: number;
    cluster_name: string;
    /** task id */
    task_id?: number;
  },
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, task_id: param1 } = params;
  return request<API.OBResponse_PrecheckTaskInfo_>(
    `/api/v1/ocp/${param0}/upgrade/precheck/${param1}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** upgrade_ocp upgrade ocp POST /api/v1/ocp/${param0}/upgrade */
export async function upgradeOcp(
  params: {
    // query
    /** ocp upgrade version */
    version: string;
    /** ocp upgrade hash */
    usable: string;
    // path
    // /** ocp id */
    // id?: number;
    cluster_name?: string;
  },
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, ...queryParams } = params;
  return request<API.OBResponse_TaskInfo_>(`/api/v1/ocp/${param0}/upgrade`, {
    method: 'POST',
    params: {
      ...queryParams,
    },
    ...(options || {}),
  });
}

/** get_ocp_upgrade_task get ocp upgrade task GET /api/v1/ocp/${param0}/upgrade/${param1} */
export async function getOcpUpgradeTask(
  params: {
    // path
    /** ocp id */
    cluster_name?: string;
    /** task id */
    task_id?: number;
  },
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, task_id: param1 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/ocp/${param0}/upgrade/${param1}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** get_ocp_upgrade_task_log get ocp upgrade task log GET /api/v1/ocp/${param0}/upgrade/${param1}/log */
export async function getOcpUpgradeTaskLog(
  params: {
    // query
    /** offset to read task log */
    offset?: number;
    // path
    cluster_name?: string;
    /** ocp id */
    // id?: number;
    /** task id */
    task_id?: number;
  },
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponse_TaskLog_>(
    `/api/v1/ocp/${param0}/upgrade/${param1}/log`,
    {
      method: 'GET',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** get_ocp_upgrade_task_report get ocp upgrade task report GET /api/v1/ocp/${param0}/upgrade/${param1}/report */
export async function getOcpUpgradeTaskReport(
  params: {
    // query
    /** offset to read task log */
    offset?: number;
    // path
    /** ocp id */
    id?: number;
    /** task id */
    task_id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponse_TaskLog_>(
    `/api/v1/ocp/${param0}/upgrade/${param1}/report`,
    {
      method: 'GET',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** get_ocp_not_upgrading_host get ocp not upgrading host GET /api/v1/ocp/upgraade/agent/hosts */
export async function getOcpNotUpgradingHost(options?: { [key: string]: any }) {
  return request<API.OBResponse_OcpUpgradeLostAddress_>(
    '/api/v1/ocp/upgraade/agent/hosts',
    {
      method: 'GET',
      ...(options || {}),
    },
  );
}

export async function getClusterNames(options?: { [key: string]: any }) {
  return request<API.ClusterNames_>('/api/v1/deployment/names', {
    method: 'GET',
    ...(options || {}),
  });
}

export async function getConnectInfo(
  params: {
    name?: number;
  },
  options?: { [key: string]: any },
) {
  const { name } = params;
  return request<API.ConnectInfo_>(
    `/api/v1/deployment/metadb/connection?name=${name}`,
    {
      method: 'GET',
      ...(options || {}),
    },
  );
}

export async function connectMetaDB(
  body?: API.DatabaseConnection,
  options?: { [key: string]: any },
) {
  return request<API.connectMetaDB_>('/api/v1/deployment/ocp/agent/ip', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  });
}

export async function createUpgradePrecheck(
  params: {
    name?: number;
  },
  options?: { [key: string]: any },
) {
  const { name } = params;
  return request<API.createUpgradePrecheck_>(
    `/api/v1/deployment/upgrade/ocp?name=${name}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      ...(options || {}),
    },
  );
}
export async function createTenants(
  params: {
    name?: string;
  },
  body?: API.OcpDeploymentConfig,
  options?: { [key: string]: any },
) {
  const { name } = params;
  return request<API.createUpgradePrecheck_>(
    `/api/v1/deployments/${name}/tenants`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      data: body,
      ...(options || {}),
    },
  );
}

export async function getTenantsTaskStatus(
  params: {
    name?: string;
    taskId?: number;
  },
  options?: { [key: string]: any },
) {
  const { name, taskId } = params;
  return request<API.OBResponse>(
    `/api/v1/deployments/${name}/tenants/${taskId}`,
    {
      method: 'GET',
      ...(options || {}),
    },
  );
}
export async function getUnitResource(
  params: {
    name?: string;
  },
  options?: { [key: string]: any },
) {
  const { name } = params;
  return request<API.OBResponse>(`/api/v1/deployments/${name}/unitresource`, {
    method: 'GET',
    ...(options || {}),
  });
}
export async function getScenario(
  params: {
    name?: string;
  },
  options?: { [key: string]: any },
) {
  const { name } = params;
  return request<API.OBResponse>(`/api/v1/deployments/${name}/scenario`, {
    method: 'GET',
    ...(options || {}),
  });
}
