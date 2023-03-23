// @ts-ignore
/* eslint-disable */
import { request } from 'umi';

/** Get Effective Mirror list remote mirrors GET /api/v1/mirrors */
export async function listRemoteMirrors(options?: { [key: string]: any }) {
  return request<API.OBResponseDataListMirror_>('/api/v1/mirrors', {
    method: 'GET',
    ...(options || {}),
  });
}

/** Get Effective Mirror get remote mirror by name GET /api/v1/mirrors/${param0} */
export async function getRemoteMirrorByName(
  // 叠加生成的Param类型 (非body参数swagger默认没有生成对象)
  params: API.getRemoteMirrorByNameParams,
  options?: { [key: string]: any },
) {
  const { section_name: param0, ...queryParams } = params;
  return request<API.OBResponseMirror_>(`/api/v1/mirrors/${param0}`, {
    method: 'GET',
    params: { ...queryParams },
    ...(options || {}),
  });
}
