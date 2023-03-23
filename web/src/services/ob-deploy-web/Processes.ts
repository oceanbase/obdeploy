// @ts-ignore
/* eslint-disable */
import { request } from 'umi';

/** Suicide finish install and kill process POST /api/v1/processes/suicide */
export async function finishInstallAndKillProcess(options?: {
  [key: string]: any;
}) {
  return request<API.OBResponse>('/api/v1/processes/suicide', {
    method: 'POST',
    ...(options || {}),
  });
}
