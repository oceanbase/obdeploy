/* eslint-disable */
// 该文件由 OneAPI 自动生成，请勿手动修改！
import { request } from 'umi';

/** get_server_info get server info GET /api/v1/info */
export async function getServerInfo(
  params: {
    // path
    /** deployment id */
    cluster_name?: string;
  },
  options?: { [key: string]: any },
) {
  const { cluster_name } = params;
  return request<API.OBResponse_ServerInfo_>(`/api/v1/upgrade/info/${cluster_name}`, {
    method: 'GET',
    ...(options || {}),
  });
}
