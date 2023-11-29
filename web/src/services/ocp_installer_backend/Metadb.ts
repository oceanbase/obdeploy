/* eslint-disable */
// 该文件由 OneAPI 自动生成，请勿手动修改！
import { request } from 'umi';

/** list_metadb_deployments list metadb deployments GET /api/v1/metadb/deployments */
export async function listMetadbDeployments(options?: { [key: string]: any }) {
  return request<API.OBResponse_DataList_MetadbDeploymentInfo__>(
    '/api/v1/metadb/deployments',
    {
      method: 'GET',
      ...(options || {}),
    },
  );
}

/** create_metadb_deployment create deployment for metadb POST /api/v1/metadb/deployments */
export async function createMetadbDeployment(
  body?: API.MetadbDeploymentConfig,
  options?: { [key: string]: any },
) {
  return request<API.OBResponse_MetadbDeploymentInfo_>(
    '/api/v1/metadb/deployments',
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

/** get_metadb_deployment get metadb deployments GET /api/v1/metadb/deployments/${param0} */
export async function getMetadbDeployment(
  params: {
    // path
    /** deployment id */
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_MetadbDeploymentInfo_>(
    `/api/v1/metadb/deployments/${param0}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** destroy_metadb destroy metadb DELETE /api/v1/metadb/deployments/${param0} */
export async function destroyMetadb(
  params: {
    // path
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/metadb/deployments/${param0}`,
    {
      method: 'DELETE',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** check machine resource check path for check GET /api/v1/metadb/deployments/${param0}/resource_check */
export async function checkMachineResource(
  params: {
    // path
    /** deployment id */
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_DataList_ResourceCheckResult__>(
    `/api/v1/metadb/deployments/${param0}/resource_check`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

export async function checkOperatingUser(
  body?: API.OperatingUser,
  options?: { [key: string]: any },
) {
  return request<API.OBResponse_OperatingUser_>('/api/v1/machine/check/user', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  });
}

/** get_metadb_deployment_resource get server resource for metadb deployment GET /api/v1/metadb/deployments/${param0}/resource */
export async function getMetadbDeploymentResource(
  params: {
    // path
    /** deployment id */
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_DataList_MetaDBResource__>(
    `/api/v1/metadb/deployments/${param0}/resource`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** precheck_metadb_deployment precheck for metadb deployment POST /api/v1/metadb/deployments/${param0}/precheck */
export async function precheckMetadbDeployment(
  params: {
    // path
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/metadb/deployments/${param0}/precheck`,
    {
      method: 'POST',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** get_metadb_precheck_task precheck for metadb deployment GET /api/v1/metadb/deployments/${param0}/precheck/${param1} */
export async function getMetadbPrecheckTask(
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
    `/api/v1/metadb/deployments/${param0}/precheck/${param1}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** recover_metadb_deployment recover metadb deployment config POST /api/v1/metadb/deployments/${param0}/recover */
export async function recoverMetadbDeployment(
  params: {
    // path
    /** deployment id */
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_DataList_RecoverChangeParameter__>(
    `/api/v1/metadb/deployments/${param0}/recover`,
    {
      method: 'POST',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** install_metadb install metadb POST /api/v1/metadb/deployments/${param0}/install */
export async function installMetadb(
  params: {
    // path
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/metadb/deployments/${param0}/install`,
    {
      method: 'POST',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** get_metadb_install_task get metadb install task GET /api/v1/metadb/deployments/${param0}/install/${param1} */
export async function getMetadbInstallTask(
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
    `/api/v1/metadb/deployments/${param0}/install/${param1}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** get_metadb_install_task_log get metadb install task log GET /api/v1/metadb/deployments/${param0}/install/${param1}/log */
export async function getMetadbInstallTaskLog(
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
    `/api/v1/metadb/deployments/${param0}/install/${param1}/log`,
    {
      method: 'GET',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** reinstall_metadb reinstall metadb POST /api/v1/metadb/deployments/${param0}/reinstall */
export async function reinstallMetadb(
  params: {
    // path
    /** deployment id */
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/metadb/deployments/${param0}/reinstall`,
    {
      method: 'POST',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** get_metadb_reinstall_task get metadb reinstall task GET /api/v1/metadb/deployments/${param0}/reinstall/${param1} */
export async function getMetadbReinstallTask(
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
    `/api/v1/metadb/deployments/${param0}/reinstall/${param1}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** get_metadb_reinstall_task_log get metadb reinstall task log GET /api/v1/metadb/deployments/${param0}/reinstall/${param1}/log */
export async function getMetadbReinstallTaskLog(
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
    `/api/v1/metadb/deployments/${param0}/reinstall/${param1}/log`,
    {
      method: 'GET',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** get_metadb_reinstall_task_report get metadb reinstall task report GET /api/v1/metadb/deployments/${param0}/reinstall/${param1}/report */
export async function getMetadbReinstallTaskReport(
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
    `/api/v1/metadb/deployments/${param0}/reinstall/${param1}/report`,
    {
      method: 'GET',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** get_metadb_destroy_task get metadb destroy task GET /api/v1/metadb/deployments/${param0}/destroy/${param1} */
export async function getMetadbDestroyTask(
  params: {
    // path
    id?: number;
    task_id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1 } = params;
  return request<API.OBResponse_TaskInfo_>(
    `/api/v1/metadb/deployments/${param0}/destroy/${param1}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}

/** list_metadb_connection list metadb connection GET /api/v1/metadb/connections */
export async function listMetadbConnection(options?: { [key: string]: any }) {
  return request<API.OBResponse_DataList_DatabaseConnection__>(
    '/api/v1/metadb/connections',
    {
      method: 'GET',
      ...(options || {}),
    },
  );
}

/** create_metadb_connection create metadb connection POST /api/v1/metadb/connections */
export async function createMetadbConnection(
  params: {
    // query
    /** whether the incoming tenant is the sys tenant */
    sys?: boolean;
  },
  body?: API.DatabaseConnection,
  options?: { [key: string]: any },
) {
  return request<API.OBResponse_DatabaseConnection_>(
    '/api/v1/metadb/connections',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      params: {
        ...params,
      },
      data: body,
      ...(options || {}),
    },
  );
}

/** get_metadb_connection get metadb connection GET /api/v1/metadb/connections/${param0} */
export async function getMetadbConnection(
  params: {
    // path
    /** connection id */
    id?: number;
  },
  options?: { [key: string]: any },
) {
  const { id: param0 } = params;
  return request<API.OBResponse_DatabaseConnection_>(
    `/api/v1/metadb/connections/${param0}`,
    {
      method: 'GET',
      params: { ...params },
      ...(options || {}),
    },
  );
}
