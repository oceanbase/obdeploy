//获取参数
export const getParamstersHandler = async (
  run: any,
  oceanbase: any,
  errorhandle: any,
) => {
  try {
    const { success, data } = await run(
      {},
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
