/* eslint-disable */
// 该文件由 OneAPI 自动生成，请勿手动修改！
import { request } from 'umi';

/** exit after a while POST /api/v1/suicide */
export async function suicide(options?: { [key: string]: any }) {
  return request<API.OBResponse>('/api/v1/suicide', {
    method: 'POST',
    ...(options || {}),
  });
}
