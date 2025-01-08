import { FormInstance } from 'antd';
/**
 * 
 * @param errorFields 待排序数组
 * @param sortArr 字段顺序
 * @returns 
 */
const sortErrorFields = (errorFields: any, sortArr: string[]) => {
  let res: any[] = [];
  for (let name of sortArr) {
    let target;
    if (name === 'dbNode') {
      target = errorFields?.find(
        (errorField: any) => !isNaN(parseFloat(errorField.name[0])),
      );
    } else {
      target = errorFields?.find(
        (errorField: any) => errorField.name[0] === name,
      );
    }
    if (target) res.push(target);
  }
  return res;
};
/**
 * 滚动聚焦于失败项
 */
const formValidScorllHelper = (
  result: [
    PromiseSettledResult<any>,
    PromiseSettledResult<API.DBConfig | undefined>,
  ],
  form: FormInstance<any>,
) => {
  let errorFields: any;
  const sortErrArr = [
    'auth',
    'launch_user',
    'ocpserver',
    'dbNode',
    'oceanbase',
    'obproxy',
  ];
  if (result[0].status === 'rejected' && result[1].status === 'rejected') {
    errorFields = result[0].reason.errorFields.toSpliced(
      2,
      0,
      ...result[1].reason.errorFields,
    );
  } else {
    errorFields =
      result[0].status === 'rejected'
        ? result[0].reason.errorFields
        : result[1].reason.errorFields;
  }
  //errorFields[0]应该是页面最上方的错误项 因此需要排序
  const sortFields = sortErrorFields(errorFields, sortErrArr);
  //数据库节点sortFields[0].name[0])为数字
  if (!isNaN(parseFloat(sortFields[0].name[0]))) {
    window.scrollTo(0, 500);
    return;
  }
  form.scrollToField(sortFields[0].name, {
    behavior: (actions) => {
      actions.forEach(({ el, top, left }) => {
        const META_SCROLLTOPS = {
          auth: 0,
          launch_user: 200,
          ocpserver: 400,
          oceanbase: 800,
          obproxy: 2200,
        };
        const scrollTop = META_SCROLLTOPS[sortFields[0].name[0]];
        el.scrollTop = scrollTop !== undefined ? scrollTop : top;
        el.scrollLeft = left;
      });
    },
  });
};

export { formValidScorllHelper, sortErrorFields };
