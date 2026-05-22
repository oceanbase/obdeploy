// @ts-ignore
/* eslint-disable */
import { request } from '@umijs/max';

/** Suicide exit after a while POST /api/v1/suicide */
export async function suicide(options?: { [key: string]: any }) {
  return request<API.OBResponse>('/api/v1/suicide', {
    method: 'POST',
    ...(options || {}),
  });
}
