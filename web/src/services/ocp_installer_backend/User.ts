/* eslint-disable */
// 该文件由 OneAPI 自动生成，请勿手动修改！
import { request } from 'umi';

/** get system user GET /api/v1/get/user */
export async function user(options?: { [key: string]: any }) {
  return request<API.OBResponse_UserInfo_>('/api/v1/get/user', {
    method: 'GET',
    ...(options || {}),
  });
}
