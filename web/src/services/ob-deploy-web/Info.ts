// @ts-ignore
/* eslint-disable */
import { request } from '@umijs/max';

/** Get Metadb Connection get connection info GET /api/v1/deployment/metadb/connection */
export async function getConnectionInfo(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getConnectionInfoParams,
  options?: { [key: string]: any },
) {
  return request<API.OBResponseDatabaseConnection_>('/api/v1/deployment/metadb/connection', {
    method: 'GET',
    params: {
      ...params,
    },
    ...(options || {}),
  });
}

/** Get Deployment Names get deployment names GET /api/v1/deployment/names */
export async function getDeploymentNames(options?: { [key: string]: any }) {
  return request<API.OBResponseDeployNames_>('/api/v1/deployment/names', {
    method: 'GET',
    ...(options || {}),
  });
}

/** Post Metadb Connection get ocp server info POST /api/v1/deployment/ocp/agent/ip */
export async function getOcpServerInfo(
  body: API.DatabaseConnection,
  options?: { [key: string]: any },
) {
  return request<API.OBResponseOcpServerInfo_>('/api/v1/deployment/ocp/agent/ip', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  });
}

/** Create Ocp Deployment get obd info POST /api/v1/deployment/upgrade/ocp */
export async function createOcpDeployment(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.createOcpDeploymentParams,
  options?: { [key: string]: any },
) {
  return request<API.OBResponse>('/api/v1/deployment/upgrade/ocp', {
    method: 'POST',
    params: {
      ...params,
    },
    ...(options || {}),
  });
}

/** Get Info get obd info GET /api/v1/info */
export async function getObdInfo(options?: { [key: string]: any }) {
  return request<API.OBResponseServiceInfo_>('/api/v1/info', {
    method: 'GET',
    ...(options || {}),
  });
}
