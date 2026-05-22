// @ts-ignore
/* eslint-disable */
import { request } from '@umijs/max';

/** Create Metadb Connection create metadb connection POST /api/v1/metadb/connections */
export async function createMetadbConnection(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.createMetadbConnectionParams,
  body: API.DatabaseConnection,
  options?: { [key: string]: any },
) {
  return request<API.OBResponseDatabaseConnection_>('/api/v1/metadb/connections', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    params: {
      ...params,
    },
    data: body,
    ...(options || {}),
  });
}

/** Get Metadb Connection get metadb connection GET /api/v1/metadb/connections/${param0} */
export async function getMetadbConnection(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getMetadbConnectionParams,
  options?: { [key: string]: any },
) {
  const { cluster_name: param0, ...queryParams } = params;
  return request<API.OBResponseDatabaseConnection_>(`/api/v1/metadb/connections/${param0}`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}
