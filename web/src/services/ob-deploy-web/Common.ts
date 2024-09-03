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

/** Suicide exit process POST /api/v1/processes/suicide */
export async function exitProcess(options?: { [key: string]: any }) {
  return request<API.OBResponse>('/api/v1/processes/suicide', {
    method: 'POST',
    ...(options || {}),
  });
}

export async function getPublicKey(){
  return request<API.OBResponse>('api/v1/keys/rsa/public')
}