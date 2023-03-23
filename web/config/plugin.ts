import { IApi } from 'umi';

export default (api: IApi) => {
  api.modifyHTML(($) => {
    // 设置 b 位
    $('body').attr('data-aspm', 'b57206');
    return $;
  });
};
