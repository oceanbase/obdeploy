//获取参数
export const getParamstersHandler = async (
  run: any,
  oceanbase: any,
  errorhandle: any,
) => {
  // component 或 version 为空时跳过请求，避免 422 错误
  if (!oceanbase?.component || !oceanbase?.version) {
    return null;
  }
  try {
    const { success, data } = await run(
      {
        filters: [
          {
            component: oceanbase?.component,
            version: oceanbase?.version,
            is_essential_only: true,
          },
        ],
      },
    );
    return { success, data };
  } catch (e: any) {
    errorhandle(e);
  }
};
