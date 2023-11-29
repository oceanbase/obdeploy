import { getLocale } from 'umi';

const docsMap = {
  'zh-CN': 'https://www.oceanbase.com/docs',
  'en-US': 'https://en.oceanbase.com/docs',
};
// 文档首页路径
export const DOCS_LINK = `/communityDocs/${docsMap[getLocale()]}/index.html`;
// 部署向导帮助文档
export const DOCS_PRODUCTION =
  'https://www.oceanbase.com/docs/community-obd-cn-1000000000314362';
// SOP文档
export const DOCS_SOP = 'https://ask.oceanbase.com/t/topic/35605473';
// 用户帮助文档
const DOCS_USER_CN =
  'https://www.oceanbase.com/docs/common-ocp-1000000000368844';
const DOCS_USER_EN =
  'https://en.oceanbase.com/docs/common-ocp-10000000001064778';
export const DOCS_USER = getLocale() === 'zh-CN' ? DOCS_USER_CN : DOCS_USER_EN;
