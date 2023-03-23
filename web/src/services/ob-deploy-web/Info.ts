// @ts-ignore
/* eslint-disable */
import { request } from 'umi';

/** Get Info get obd info GET /api/v1/info */
export async function getObdInfo(options?: { [key: string]: any }) {
  return request<API.OBResponseServiceInfo_>('/api/v1/info', {
    method: 'GET',
    ...(options || {}),
  });
}
