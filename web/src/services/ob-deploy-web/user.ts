// @ts-ignore
/* eslint-disable */
import { request } from '@umijs/max';

/** Get User get system user GET /api/v1/get/user */
export async function user(options?: { [key: string]: any }) {
  return request<API.OBResponseUserInfo_>('/api/v1/get/user', {
    method: 'GET',
    ...(options || {}),
  });
}
