// @ts-ignore
/* eslint-disable */
import { getQueryFromComps } from '@/utils/helper';
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
  const { name: param0, component_name, force } = params;
  return request<API.OBResponse>(
    `/api/v1/component_change/${param0}?${getQueryFromComps(
      component_name,
    )}&force=${force}`,
    {
      method: 'DELETE',
      ...(options || {}),
    },
  );
}

/** Get Component Change Task get task res of component change GET /api/v1/component_change/${param0}/component_change */
export async function componentChangeTask(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeTaskParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponseTaskInfo_>(
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
  const { name: param0, component_name } = params;
  return request<API.OBResponseInstallLog_>(
    `/api/v1/component_change/${param0}/del?${getQueryFromComps(
      component_name,
    )}`,
    {
      method: 'GET',
      ...(options || {}),
    },
  );
}

/** Get Del Component Change Task get task res of component change GET /api/v1/component_change/${param0}/del_component */
export async function componentChangeTask2(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeTaskParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(
    `/api/v1/component_change/${param0}/del_component`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Create Deployment create scale_out/component_add config POST /api/v1/component_change/${param0}/deployment */
export async function componentChangeConfig(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.ComponentChangeConfigParams,
  body: API.ComponentChangeConfig,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(
    `/api/v1/component_change/${param0}/deployment`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      params: { ...queryParams },
      data: body,
      ...(options || {}),
    },
  );
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
  const { name: param0, component_name } = params;
  return request<API.OBResponseComponentsServer_>(
    `/api/v1/component_change/${param0}/node/check?${getQueryFromComps(
      component_name,
    )}`,
    {
      method: 'POST',
      ...(options || {}),
    },
  );
}

/** Get Component Change Precheck Task get result of scale_out/component_add precheck GET /api/v1/component_change/${param0}/precheck */
export async function precheckComponentChangeRes(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.PrecheckComponentChangeResParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponsePreCheckResult_>(
    `/api/v1/component_change/${param0}/precheck`,
    {
      method: 'GET',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Precheck Component Change Deployment precheck for scale_out/component_add deployment POST /api/v1/component_change/${param0}/precheck */
export async function precheckComponentChange(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.PrecheckComponentChangeParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(
    `/api/v1/component_change/${param0}/precheck`,
    {
      method: 'POST',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Recover Deployment recover scale_out/component_add config POST /api/v1/component_change/${param0}/recover */
export async function recoverComponentChange(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.RecoverComponentChangeParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponseDataListRecoverChangeParameter_>(
    `/api/v1/component_change/${param0}/recover`,
    {
      method: 'POST',
      params: { ...queryParams },
      ...(options || {}),
    },
  );
}

/** Remove Component remove component GET /api/v1/component_change/${param0}/remove */
export async function removeComponent(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.RemoveComponentParams,
  options?: { [key: string]: any },
) {
  const { name: param0, components } = params;
  return request<API.OBResponse>(
    `/api/v1/component_change/${param0}/remove?${getQueryFromComps(
      components,
    )}`,
    {
      method: 'POST',
      ...(options || {}),
    },
  );
}

/** Get Deployments get scale_out/component_add deployments name GET /api/v1/component_change/deployment */
export async function componentChangeDeploymentsName(options?: {
  [key: string]: any;
}) {
  return request<API.OBResponseDataListDeployName_>(
    '/api/v1/component_change/deployment',
    {
      method: 'GET',
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
  const formatComp = (componentsList?: API.BestComponentInfo[]) => {
    if (!componentsList || !componentsList.length) return componentsList;
    componentsList.sort((pre, cur) => pre.deployed - cur.deployed);
    const prometheus = componentsList.find(
      (item) => item.component_name === 'prometheus',
    );
    const grafana = componentsList.find(
      (item) => item.component_name === 'grafana',
    );
    if (!prometheus?.deployed) {
      const index = componentsList.findIndex(
        (item) => item.component_name === 'prometheus',
      );
      componentsList.splice(index, 1);
    }
    if (!grafana?.deployed) {
      const index = componentsList.findIndex(
        (item) => item.component_name === 'grafana',
      );
      componentsList.splice(index, 1);
    }
  };
  const res = await request<API.OBResponseComponentChangeInfo_>(
    '/api/v1/component_change/deployment/detail',
    {
      method: 'GET',
      params: {
        ...params,
      },
      ...(options || {}),
    },
  );
  if (res.success) {
    formatComp(res.data?.component_list);
  }
  return res;
}

export async function componentChangeDepends(params: { name: string }) {
  return request<API.ComponentsDepends_>(
    '/api/v1/component_change/deployment/depends',
    {
      method: 'GET',
      params,
    },
  );
}

export async function getCommondConfigPath(name:string){
  return request<API.CommondConfigPath>(
    `/api/v1/component_change/${name}/path`,
    {
      method: 'GET',
    },
  );
}