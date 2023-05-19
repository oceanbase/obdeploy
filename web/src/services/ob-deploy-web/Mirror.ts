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
