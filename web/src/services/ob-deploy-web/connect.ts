// @ts-ignore
/* eslint-disable */
import { request } from '@umijs/max';

/** Create Metadb Connection check influx connect POST /api/v1/connect/influxdb */
export async function checkInfluxConnect(
  body: API.BodyCheckInfluxConnect,
  options?: { [key: string]: any },
) {
  return request<API.OBResponse>('/api/v1/connect/influxdb', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
    ...(options || {}),
  });
}
