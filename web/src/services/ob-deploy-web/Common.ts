// @ts-ignore
/* eslint-disable */
import { request } from '@umijs/max';

/** Keep Alive validate or set keep alive token POST /api/v1/connect/keep_alive */
export async function validateOrSetKeepAliveToken(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.validateOrSetKeepAliveTokenParams,
  options?: { [key: string]: any },
) {
  return request<API.OBResponse>('/api/v1/connect/keep_alive', {
    method: 'POST',
    params: {
      ...params,
    },
    ...(options || {}),
  });
}

/** Get Current User get current running user GET /api/v1/current/user */
export async function getCurrentRunningUser(options?: { [key: string]: any }) {
  return request<API.OBResponse>('/api/v1/current/user', {
    method: 'GET',
    ...(options || {}),
  });
}

/** Public Key rsa public key GET /api/v1/keys/rsa/public */
export async function rsaPublicKey(options?: { [key: string]: any }) {
  return request<API.OBResponse>('/api/v1/keys/rsa/public', {
    method: 'GET',
    ...(options || {}),
  });
}

/** Suicide exit process POST /api/v1/processes/suicide */
export async function exitProcess(options?: { [key: string]: any }) {
  return request<API.OBResponse>('/api/v1/processes/suicide', {
    method: 'POST',
    ...(options || {}),
  });
}

/** Get Telemetry Data get telemetry data GET /api/v1/telemetry/${param0} */
export async function getTelemetryData(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getTelemetryDataParams,
  options?: { [key: string]: any },
) {
  const { name: param0, ...queryParams } = params;
  return request<API.OBResponse>(`/api/v1/telemetry/${param0}`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}

/** Get Web Type get web type GET /api/v1/web/types */
export async function getWebType(options?: { [key: string]: any }) {
  return request<API.OBResponse>('/api/v1/web/types', {
    method: 'GET',
    ...(options || {}),
  });
}

// 居中兼容别名
export const getPublicKey = rsaPublicKey;
