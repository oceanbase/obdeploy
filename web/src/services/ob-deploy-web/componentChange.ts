// @ts-ignore
/* eslint-disable */
import { request } from '@umijs/max';

/** Component Change component change POST /api/v1/component_change/${param0} */
export async function componentChange(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeParams,
  body: API.ComponentChangeMode,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/component_change/${param0}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    params: { ...queryParams },
    data: body,
    ...(options || {}),
  });
}

/** Del Component del componnet DELETE /api/v1/component_change/${param0} */
export async function componentChangeDelComponent(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeDelComponentParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/component_change/${param0}`, {
    method: 'DELETE',
    params: {
      ...queryParams,
    },
    ...(options || {}),
  });
}

/** Get Component Change Task get task res of component change GET /api/v1/component_change/${param0}/component_change */
export async function componentChangeTask(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeTaskParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.service_api_v1_deployments_OBResponseTaskInfo>(
    `/api/v1/component_change/${param0}/component_change`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Get Component Change Log get log of component change GET /api/v1/component_change/${param0}/component_change/log */
export async function componentChangeLog(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeLogParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponseInstallLog_>(
    `/api/v1/component_change/${param0}/component_change/log`,
    {
      method: 'GET',
      params: {
        ...queryParams,
      },
      ...(options || {}),
    },
  );
}

/** Get Del Component Log get del component task GET /api/v1/component_change/${param0}/del */
export async function componentChangeDelComponentTask(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeDelComponentTaskParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/component_change/${param0}/del`, {
    method: 'GET',
    params: {
      ...queryParams,
    },
    ...(options || {}),
  });
}

/** Get Del Component Change Task get task res of component change GET /api/v1/component_change/${param0}/del_component */
export async function componentChangeTask2(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeTaskParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/component_change/${param0}/del_component`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Create Deployment create scale_out/component_add config POST /api/v1/component_change/${param0}/deployment */
export async function componentChangeConfig(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeConfigParams,
  body: API.ComponentChangeConfig,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/component_change/${param0}/deployment`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    params: { ...queryParams },
    data: body,
    ...(options || {}),
  });
}

/** Get Component Change Detail del component with node check POST /api/v1/component_change/${param0}/display */
export async function componentChangeNodeCheck(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeNodeCheckParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponseComponentsChangeInfoDisplay_>(
    `/api/v1/component_change/${param0}/display`,
    {
      method: 'POST',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Node Check del component with node check POST /api/v1/component_change/${param0}/node/check */
export async function componentChangeNodeCheck2(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeNodeCheckParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponseComponentsServer_>(`/api/v1/component_change/${param0}/node/check`, {
    method: 'POST',
    params: {
      ...queryParams,
    },
    ...(options || {}),
  });
}

/** Get Config Path get config path GET /api/v1/component_change/${param0}/path */
export async function getConfigPath(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.GetConfigPathParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponseConfigPath_>(`/api/v1/component_change/${param0}/path`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Get Component Change Precheck Task get result of scale_out/component_add precheck GET /api/v1/component_change/${param0}/precheck */
export async function precheckComponentChangeRes(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.PrecheckComponentChangeResParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponsePreCheckResult_>(`/api/v1/component_change/${param0}/precheck`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Precheck Component Change Deployment precheck for scale_out/component_add deployment POST /api/v1/component_change/${param0}/precheck */
export async function precheckComponentChange(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.PrecheckComponentChangeParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/component_change/${param0}/precheck`, {
    method: 'POST',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Recover Deployment recover scale_out/component_add config POST /api/v1/component_change/${param0}/recover */
export async function recoverComponentChange(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.RecoverComponentChangeParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.service_api_v1_ocpDeployments_OBResponseDataListRecoverChangeParameter>(
    `/api/v1/component_change/${param0}/recover`,
    {
      method: 'POST',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Remove Component remove component POST /api/v1/component_change/${param0}/remove */
export async function removeComponent(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.RemoveComponentParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/component_change/${param0}/remove`, {
    method: 'POST',
    params: {
      ...queryParams,
    },
    ...(options || {}),
  });
}

/** Get Deployments get scale_out/component_add deployments name GET /api/v1/component_change/deployment */
export async function componentChangeDeploymentsName(options?: { [key: string]: any }) {
  return request<API.OBResponseDataListDeployName_>('/api/v1/component_change/deployment', {
    method: 'GET',
    ...(options || {}),
  });
}

/** Get Deployment Depends get scale_out/component_add deployments info GET /api/v1/component_change/deployment/depends */
export async function componentChangeDeploymentsInfo2(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeDeploymentsInfoParams,
  options?: { [key: string]: any },
) {
  return request<API.OBResponseDataListComponentDepends_>(
    '/api/v1/component_change/deployment/depends',
    {
      method: 'GET',
      params: {
        ...params,
      },
      ...(options || {}),
    },
  );
}

/** Get Deployments get scale_out/component_add deployments info GET /api/v1/component_change/deployment/detail */
export async function componentChangeDeploymentsInfo(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeDeploymentsInfoParams,
  options?: { [key: string]: any },
) {
  return request<API.OBResponseComponentChangeInfo_>('/api/v1/component_change/deployment/detail', {
    method: 'GET',
    params: {
      ...params,
    },
    ...(options || {}),
  });
}
