// @ts-ignore
/* eslint-disable */
import { request } from '@umijs/max';

/** Get Deployments get deployment GET /api/v1/deployments */
export async function getDeployment(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getDeploymentParams,
  options?: { [key: string]: any },
) {
  return request<API.OBResponseDataListDeployment_>('/api/v1/deployments', {
    method: 'GET',
    params: {
      ...params,
    },
    ...(options || {}),
  });
}

/** Get Destroy Task Info get destroy task info GET /api/v1/deployments_test */
export async function getDestroyTaskInfo2(options?: { [key: string]: any }) {
  return request<API.OBResponse>('/api/v1/deployments_test', {
    method: 'GET',
    ...(options || {}),
  });
}

/** Get Deployment query deployment config GET /api/v1/deployments/${param0} */
export async function queryDeploymentConfig(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.queryDeploymentConfigParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponseDeploymentInfo_>(`/api/v1/deployments/${param0}`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Create Deployment create deployment config POST /api/v1/deployments/${param0} */
export async function createDeploymentConfig(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.createDeploymentConfigParams,
  body: API.DeploymentConfig,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/deployments/${param0}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    params: { ...queryParams },
    data: body,
    ...(options || {}),
  });
}

/** Destroy Deployment destroy deployment DELETE /api/v1/deployments/${param0} */
export async function destroyDeployment(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.destroyDeploymentParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/deployments/${param0}`, {
    method: 'DELETE',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Get Connect Info query connect info GET /api/v1/deployments/${param0}/connection */
export async function queryConnectionInfo(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.queryConnectionInfoParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponseDataListConnectionInfo_>(
    `/api/v1/deployments/${param0}/connection`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Destroy Task Info get destroy task info GET /api/v1/deployments/${param0}/destroy */
export async function getDestroyTaskInfo(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getDestroyTaskInfoParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.service_api_v1_deployments_OBResponseTaskInfo>(
    `/api/v1/deployments/${param0}/destroy`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Detail get one deployment detail GET /api/v1/deployments/${param0}/detail */
export async function queryDeploymentDetail(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.queryDeploymentDetailParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/deployments/${param0}/detail`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Get Install Status query install status GET /api/v1/deployments/${param0}/install */
export async function queryInstallStatus(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.queryInstallStatusParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.service_api_v1_deployments_OBResponseTaskInfo>(
    `/api/v1/deployments/${param0}/install`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Install deploy and start a deployment POST /api/v1/deployments/${param0}/install */
export async function deployAndStartADeployment(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.deployAndStartADeploymentParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/deployments/${param0}/install`, {
    method: 'POST',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Get Install Log query install log GET /api/v1/deployments/${param0}/install/log */
export async function queryInstallLog(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.queryInstallLogParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponseInstallLog_>(`/api/v1/deployments/${param0}/install/log`, {
    method: 'GET',
    params: {
      ...queryParams,
    },
    ...(options || {}),
  });
}

/** Get Pre Check Status select pre-check status by pre deployment name GET /api/v1/deployments/${param0}/precheck */
export async function preCheckStatus(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.preCheckStatusParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponsePreCheckResult_>(`/api/v1/deployments/${param0}/precheck`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Pre Check pre-check, asynchronous process POST /api/v1/deployments/${param0}/precheck */
export async function preCheck(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.preCheckParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/deployments/${param0}/precheck`, {
    method: 'POST',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Recover recover POST /api/v1/deployments/${param0}/recover */
export async function recover(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.recoverParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.service_api_v1_deployments_OBResponseDataListRecoverChangeParameter>(
    `/api/v1/deployments/${param0}/recover`,
    {
      method: 'POST',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Deployment Report query deployment report GET /api/v1/deployments/${param0}/report */
export async function queryDeploymentReport(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.queryDeploymentReportParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponseDataListDeploymentReport_>(`/api/v1/deployments/${param0}/report`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Get Tenant Scenario get tenant scenario GET /api/v1/deployments/${param0}/scenario */
export async function getTenantScenario(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getTenantScenarioParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponseDataListScenarioType_>(`/api/v1/deployments/${param0}/scenario`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Get Start Status query start status GET /api/v1/deployments/${param0}/start */
export async function queryStartStatus(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.queryStartStatusParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.service_api_v1_deployments_OBResponseTaskInfo>(
    `/api/v1/deployments/${param0}/start`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Start start a deployment POST /api/v1/deployments/${param0}/start */
export async function startADeployment(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.startADeploymentParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/deployments/${param0}/start`, {
    method: 'POST',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Get Start Log query start log GET /api/v1/deployments/${param0}/start/log */
export async function queryStartLog(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.queryStartLogParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponseInstallLog_>(`/api/v1/deployments/${param0}/start/log`, {
    method: 'GET',
    params: {
      ...queryParams,
    },
    ...(options || {}),
  });
}

/** Get Start Status query stop status GET /api/v1/deployments/${param0}/stop */
export async function queryStopStatus(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.queryStopStatusParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.service_api_v1_deployments_OBResponseTaskInfo>(
    `/api/v1/deployments/${param0}/stop`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Stop stop a deployment POST /api/v1/deployments/${param0}/stop */
export async function stopADeployment(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.stopADeploymentParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/deployments/${param0}/stop`, {
    method: 'POST',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Get Stop Log query stop log GET /api/v1/deployments/${param0}/stop/log */
export async function queryStopLog(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.queryStopLogParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponseInstallLog_>(`/api/v1/deployments/${param0}/stop/log`, {
    method: 'GET',
    params: {
      ...queryParams,
    },
    ...(options || {}),
  });
}

/** Create Tenant create tenant POST /api/v1/deployments/${param0}/tenants */
export async function createTenant(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.createTenantParams,
  body: API.CreateTenantConfig,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/deployments/${param0}/tenants`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    params: { ...queryParams },
    data: body,
    ...(options || {}),
  });
}

/** Unit Resource unit resource GET /api/v1/deployments/${param0}/unitresource */
export async function unitResource(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.unitResourceParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/deployments/${param0}/unitresource`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Get Create Tenant Task create tenant task info GET /api/v1/deployments/${param1}/tenants/${param0} */
export async function createTenantTaskInfo(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.createTenantTaskInfoParams,
  options?: { [key: string]: any },
) {
  const { task_id: param0, name: param1, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/deployments/${param1}/tenants/${param0}`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Get Install Log query create tenant log GET /api/v1/deployments/${param1}/tenants/${param0}/log */
export async function queryCreateTenantLog(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.queryCreateTenantLogParams,
  options?: { [key: string]: any },
) {
  const { task_id: param0, name: param1, ...queryParams } = params;
  return request<API.OBResponseInstallLog_>(`/api/v1/deployments/${param1}/tenants/${param0}/log`, {
    method: 'GET',
    params: {
      ...queryParams,
    },
    ...(options || {}),
  });
}

/** Get Destroy Task Info get scenario GET /api/v1/deployments/scenario/type */
export async function getScenario(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getScenarioParams,
  options?: { [key: string]: any },
) {
  return request<API.OBResponseDataListScenarioType_>('/api/v1/deployments/scenario/type', {
    method: 'GET',
    params: {
      ...params,
    },
    ...(options || {}),
  });
}

// 居中兼容别名
export const getScenarioType = getScenario;
