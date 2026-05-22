// @ts-ignore
/* eslint-disable */
import { request } from '@umijs/max';

/** Takeover Oms takeover oms POST /api/v1/oms/${param0}/takeover */
export async function takeoverOms(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.takeoverOmsParams,
  body: API.BodyTakeoverOms,
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/oms/${param0}/takeover`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    params: { ...queryParams },
    data: body,
    ...(options || {}),
  });
}

/** Upgrade Oms upgrade oms POST /api/v1/oms/${param0}/upgrade */
export async function upgradeOms(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.upgradeOmsParams,
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/oms/${param0}/upgrade`,
    {
      method: 'POST',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** Get Oms Upgrade Task get oms upgrade task GET /api/v1/oms/${param0}/upgrade/${param1} */
export async function getOmsUpgradeTask(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOmsUpgradeTaskParams,
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, task_id: param1, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/oms/${param0}/upgrade/${param1}`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Oms Upgrade Task Log get oms upgrade task log GET /api/v1/oms/${param0}/upgrade/${param1}/log */
export async function getOmsUpgradeTaskLog(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOmsUpgradeTaskLogParams,
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponseTaskLog_>(`/api/v1/oms/${param0}/upgrade/${param1}/log`, {
    method: 'GET',
    params: {
      ...queryParams,
    },
    ...(options || {}),
  });
}

/** Precheck Oms Upgrade precheck for oms upgrade POST /api/v1/oms/${param0}/upgrade/precheck */
export async function precheckOmsUpgrade(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.precheckOmsUpgradeParams,
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/oms/${param0}/upgrade/precheck`,
    {
      method: 'POST',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** Get Oms Upgrade Precheck Task get precheck for oms upgrade GET /api/v1/oms/${param0}/upgrade/precheck/${param1} */
export async function getOmsUpgradePrecheckTask(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOmsUpgradePrecheckTaskParams,
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponsePrecheckTaskInfo_>(
    `/api/v1/oms/${param0}/upgrade/precheck/${param1}`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Oms Deployments get oms deployments GET /api/v1/oms/deployments */
export async function getOmsDeployments(options?: { [key: string]: any }) {
  return request<API.OBResponse>('/api/v1/oms/deployments', {
    method: 'GET',
    ...(options || {}),
  });
}

/** Destroy Oms destroy oms DELETE /api/v1/oms/deployments/${param0} */
export async function destroyOms(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.destroyOmsParams,
  options?: { [key: string]: any },
) {
  const { id: param0, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/oms/deployments/${param0}`,
    {
      method: 'DELETE',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Oms Destroy Task get oms destroy task GET /api/v1/oms/deployments/${param0}/destroy/${param1} */
export async function getOmsDestroyTask(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOmsDestroyTaskParams,
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/oms/deployments/${param0}/destroy/${param1}`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Install Oms install oms POST /api/v1/oms/deployments/${param0}/install */
export async function installOms(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.installOmsParams,
  options?: { [key: string]: any },
) {
  const { id: param0, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/oms/deployments/${param0}/install`,
    {
      method: 'POST',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Oms Install Task get oms install task GET /api/v1/oms/deployments/${param0}/install/${param1} */
export async function getOmsInstallTask(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOmsInstallTaskParams,
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/oms/deployments/${param0}/install/${param1}`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Oms Install Task Log get oms install task log GET /api/v1/oms/deployments/${param0}/install/${param1}/log */
export async function getOmsInstallTaskLog(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOmsInstallTaskLogParams,
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponseTaskLog_>(
    `/api/v1/oms/deployments/${param0}/install/${param1}/log`,
    {
      method: 'GET',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** Precheck Oms Deployment precheck for oms deployment POST /api/v1/oms/deployments/${param0}/precheck */
export async function precheckOmsDeployment(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.precheckOmsDeploymentParams,
  options?: { [key: string]: any },
) {
  const { id: param0, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/oms/deployments/${param0}/precheck`,
    {
      method: 'POST',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Oms Precheck Task precheck for oms deployment GET /api/v1/oms/deployments/${param0}/precheck/${param1} */
export async function precheckOms(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.precheckOmsParams,
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponsePrecheckTaskInfo_>(
    `/api/v1/oms/deployments/${param0}/precheck/${param1}`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Reinstall Oms reinstall oms POST /api/v1/oms/deployments/${param0}/reinstall */
export async function reinstallOms(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.reinstallOmsParams,
  options?: { [key: string]: any },
) {
  const { id: param0, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/oms/deployments/${param0}/reinstall`,
    {
      method: 'POST',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Oms Reinstall Task get oms reinstall task GET /api/v1/oms/deployments/${param0}/reinstall/${param1} */
export async function getOmsReinstallTask(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOmsReinstallTaskParams,
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.service_api_v1_omsDeployments_OBResponseTaskInfo>(
    `/api/v1/oms/deployments/${param0}/reinstall/${param1}`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Oms Reinstall Task Log get oms reinstall task log GET /api/v1/oms/deployments/${param0}/reinstall/${param1}/log */
export async function getOmsReinstallTaskLog(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getOmsReinstallTaskLogParams,
  options?: { [key: string]: any },
) {
  const { id: param0, task_id: param1, ...queryParams } = params;
  return request<API.OBResponseTaskLog_>(
    `/api/v1/oms/deployments/${param0}/reinstall/${param1}/log`,
    {
      method: 'GET',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** Get Usable Oms Docker Images get oms login url GET /api/v1/oms/display */
export async function getOmsLoginUrl(options?: { [key: string]: any }) {
  return request<API.OBResponse>('/api/v1/oms/display', {
    method: 'GET',
    ...(options || {}),
  });
}

/** Get Usable Oms Docker Images get_usable_oms_docker_images GET /api/v1/oms/docker_images */
export async function getUsableOmsDockerImages(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getUsableOmsDockerImagesParams,
  options?: { [key: string]: any },
) {
  return request<API.OBResponse>('/api/v1/oms/docker_images', {
    method: 'GET',
    params: {
      ...params,
    },
    ...(options || {}),
  });
}

/** Create Deployment create oms deployment config POST /api/v1/oms/generate_config/${param0} */
export async function createOmsDeploymentConfig(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.createOmsDeploymentConfigParams,
  body: API.OmsDeploymentConfig,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/oms/generate_config/${param0}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    params: { ...queryParams },
    data: body,
    ...(options || {}),
  });
}

/** Backup Oms backup oms POST /api/v1/oms/meta/backup */
export async function backupOms(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.backupOmsParams,
  options?: { [key: string]: any },
) {
  return request<API.OBResponse>('/api/v1/oms/meta/backup', {
    method: 'POST',
    params: {
      ...params,
    },
    ...(options || {}),
  });
}

/** Get Oms Upgrade Info get upgrade info GET /api/v1/oms/upgrade/${param0}/info */
export async function getUpgradeInfo(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getUpgradeInfoParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/oms/upgrade/${param0}/info`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

// 居中兼容别名
export const queryInstallStatusOms = getOmsInstallTask;
export const queryInstallLogOms = getOmsInstallTaskLog;
export const creatOmsDeploymentConfig = createOmsDeploymentConfig;
