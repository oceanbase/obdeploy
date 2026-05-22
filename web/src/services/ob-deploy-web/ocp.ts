// @ts-ignore
/* eslint-disable */
import { request } from '@umijs/max';

/** Check User Check if the user input exists POST /api/v1/machine/check/user */
export async function machineUser(body: API.UserCheck, options?: { [key: string]: any }) {
  return request<API.OBResponse>('/api/v1/machine/check/user', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  });
}

/** Create Ocp Info create ocp info POST /api/v1/ocp */
export async function createOcpInfo(
  body: API.DatabaseConnection,
  options?: { [key: string]: any },
) {
  return request<API.OBResponseOcpInfo_>('/api/v1/ocp', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  });
}

/** Create Deployment create ocp deployment config POST /api/v1/ocp_deployments/${param0} */
export async function createOcpDeploymentConfig(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.createOcpDeploymentConfigParams,
  body: API.OCPDeploymnetConfig,
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

/** Get Ocp Info get ocp info GET /api/v1/ocp/${param0} */
export async function getOcpInfo(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOcpInfoParams,
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, ...queryParams } = params;
  return request<API.OBResponseOcpInfo_>(`/api/v1/ocp/${param0}`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Upgrade Ocp upgrade ocp POST /api/v1/ocp/${param0}/upgrade */
export async function upgradeOcp(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.upgradeOcpParams,
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/ocp/${param0}/upgrade`,
    {
      method: 'POST',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** Get Ocp Upgrade Task get ocp upgrade task GET /api/v1/ocp/${param0}/upgrade/${param1} */
export async function getOcpUpgradeTask(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOcpUpgradeTaskParams,
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, task_id: param1, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/ocp/${param0}/upgrade/${param1}`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Ocp Upgrade Task Log get ocp upgrade task log GET /api/v1/ocp/${param0}/upgrade/${param1}/log */
export async function getOcpUpgradeTaskLog(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOcpUpgradeTaskLogParams,
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponseTaskLog_>(`/api/v1/ocp/${param0}/upgrade/${param1}/log`, {
    method: 'GET',
    params: {
      ...queryParams,
    },
    ...(options || {}),
  });
}

/** Precheck Ocp Upgrade post precheck for ocp upgrade POST /api/v1/ocp/${param0}/upgrade/precheck */
export async function precheckOcpUpgrade(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.precheckOcpUpgradeParams,
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/ocp/${param0}/upgrade/precheck`,
    {
      method: 'POST',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Ocp Upgrade Precheck Task get precheck for ocp upgrade GET /api/v1/ocp/${param0}/upgrade/precheck/${param1} */
export async function getOcpUpgradePrecheckTask(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOcpUpgradePrecheckTaskParams,
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponsePrecheckTaskInfo_>(
    `/api/v1/ocp/${param0}/upgrade/precheck/${param1}`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Destroy Ocp destroy ocp DELETE /api/v1/ocp/deployments/${param0} */
export async function destroyOcp(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.destroyOcpParams,
  options?: { [key: string]: any },
) {
  const { id: param0, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/ocp/deployments/${param0}`,
    {
      method: 'DELETE',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Ocp Destroy Task get ocp destroy task GET /api/v1/ocp/deployments/${param0}/destroy/${param1} */
export async function getOcpDestroyTask(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOcpDestroyTaskParams,
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/ocp/deployments/${param0}/destroy/${param1}`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Install Ocp install ocp POST /api/v1/ocp/deployments/${param0}/install */
export async function installOcp(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.installOcpParams,
  options?: { [key: string]: any },
) {
  const { id: param0, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/ocp/deployments/${param0}/install`,
    {
      method: 'POST',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Ocp Install Task get ocp install task GET /api/v1/ocp/deployments/${param0}/install/${param1} */
export async function getOcpInstallTask(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOcpInstallTaskParams,
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/ocp/deployments/${param0}/install/${param1}`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Ocp Install Task Log get ocp install task log GET /api/v1/ocp/deployments/${param0}/install/${param1}/log */
export async function getOcpInstallTaskLog(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOcpInstallTaskLogParams,
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponseTaskLog_>(
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

/** Precheck Ocp Deployment precheck for ocp deployment POST /api/v1/ocp/deployments/${param0}/precheck */
export async function precheckOcpDeployment(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.precheckOcpDeploymentParams,
  options?: { [key: string]: any },
) {
  const { id: param0, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/ocp/deployments/${param0}/precheck`,
    {
      method: 'POST',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Ocp Precheck Task precheck for ocp deployment GET /api/v1/ocp/deployments/${param0}/precheck/${param1} */
export async function precheckOcp(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.precheckOcpParams,
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponsePrecheckTaskInfo_>(
    `/api/v1/ocp/deployments/${param0}/precheck/${param1}`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Recover Ocp Deployment recover ocp deployment config POST /api/v1/ocp/deployments/${param0}/recover */
export async function recoverOcpDeployment(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.recoverOcpDeploymentParams,
  options?: { [key: string]: any },
) {
  const { id: param0, ...queryParams } = params;
  return request<API.service_api_v1_ocpDeployments_OBResponseDataListRecoverChangeParameter>(
    `/api/v1/ocp/deployments/${param0}/recover`,
    {
      method: 'POST',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Reinstall Ocp reinstall ocp POST /api/v1/ocp/deployments/${param0}/reinstall */
export async function reinstallOcp(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.reinstallOcpParams,
  options?: { [key: string]: any },
) {
  const { id: param0, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/ocp/deployments/${param0}/reinstall`,
    {
      method: 'POST',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Ocp Reinstall Task get ocp reinstall task GET /api/v1/ocp/deployments/${param0}/reinstall/${param1} */
export async function getOcpReinstallTask(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOcpReinstallTaskParams,
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/ocp/deployments/${param0}/reinstall/${param1}`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Ocp Reinstall Task Log get ocp reinstall task log GET /api/v1/ocp/deployments/${param0}/reinstall/${param1}/log */
export async function getOcpReinstallTaskLog(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOcpReinstallTaskLogParams,
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponseTaskLog_>(
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

/** Get Installed Ocp Info get_installed_ocp_info GET /api/v1/ocp/info/${param0} */
export async function getInstalledOcpInfo(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getInstalledOcpInfoParams,
  options?: { [key: string]: any },
) {
  const { id: param0, ...queryParams } = params;
  return request<API.OBResponseOcpInstalledInfo_>(`/api/v1/ocp/info/${param0}`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Get Ocp Upgrade Task Log get ocp not upgrading host GET /api/v1/ocp/upgraade/agent/hosts */
export async function getOcpNotUpgradingHost(options?: { [key: string]: any }) {
  return request<API.OBResponseOcpUpgradeLostAddress_>('/api/v1/ocp/upgraade/agent/hosts', {
    method: 'GET',
    ...(options || {}),
  });
}
