// import { getLocale } from '@umijs/max';

export function getDocs(getLocale) {
  const docsMap = {
    'zh-CN': 'https://www.oceanbase.com/docs',
    'en-US': 'https://en.oceanbase.com/docs',
  };

  // 文档首页路径
  const DOCS_LINK = `/communityDocs/${docsMap[getLocale()]}/index.html`;

  // 用户帮助文档
  const DOCS_USER_CN =
    'https://www.oceanbase.com/docs/common-ocp-1000000000368844';
  const DOCS_USER_EN =
    'https://en.oceanbase.com/docs/common-ocp-10000000001064778';
  const DOCS_USER = getLocale() === 'zh-CN' ? DOCS_USER_CN : DOCS_USER_EN;

  //官网
  const OFFICAIL_WEBSITE_CN = 'https://www.oceanbase.com/';
  const OFFICAIL_WEBSITE_EN = 'https://en.oceanbase.com/';
  const OFFICAIL_WEBSITE =
    getLocale() === 'zh-CN' ? OFFICAIL_WEBSITE_CN : OFFICAIL_WEBSITE_EN;

  //访问论坛
  const FORUMS_VISITED_CN = 'https://ask.oceanbase.com/';
  const FORUMS_VISITED_EN = 'https://github.com/oceanbase/obdeploy';
  const FORUMS_VISITED =
    getLocale() === 'zh-CN' ? FORUMS_VISITED_CN : FORUMS_VISITED_EN;

  //帮助中心
  const HELP_CENTER_CN = 'https://www.oceanbase.com/docs/obd-cn';
  const HELP_CENTER_EN = 'https://en.oceanbase.com/docs/obd-en';
  const HELP_CENTER = getLocale() === 'zh-CN' ? HELP_CENTER_CN : HELP_CENTER_EN;

  //OBD
  const OBD_DOCS_CN = 'https://www.oceanbase.com/docs/oceanbase-database-cn';
  const OBD_DOCS_EN = 'https://en.oceanbase.com/docs/oceanbase-database';
  const OBD_DOCS = getLocale() === 'zh-CN' ? OBD_DOCS_CN : OBD_DOCS_EN;

  //OCP Express
  const OCP_EXPRESS_CN =
    'https://www.oceanbase.com/docs/common-oceanbase-database-cn-1000000001050397';
  const OCP_EXPRESS_EN =
    'https://en.oceanbase.com/docs/common-oceanbase-database-10000000001375615';
  const OCP_EXPRESS = getLocale() === 'zh-CN' ? OCP_EXPRESS_CN : OCP_EXPRESS_EN;

  //OCP
  const OCP_DOCS_CN = 'https://www.oceanbase.com/docs/ocp';
  const OCP_DOCS_EN = 'https://en.oceanbase.com/docs/ocp-en';
  const OCP_DOCS = getLocale() === 'zh-CN' ? OCP_DOCS_CN : OCP_DOCS_EN;

  //OBAgent
  const OBAGENT_DOCS = 'https://github.com/oceanbase/obagent';

  //OBProxy
  const OBPROXY_DOCS_CN = 'https://www.oceanbase.com/docs/odp-doc-cn';
  const OBPROXY_DOCS_EN = 'https://en.oceanbase.com/docs/odp-en';
  const OBPROXY_DOCS =
    getLocale() === 'zh-CN' ? OBPROXY_DOCS_CN : OBPROXY_DOCS_EN;

  const OBCONFIGSERVER_DOCS =
    'https://github.com/oceanbase/oceanbase/tree/master/tools/ob-configserver';

  //模式配置规则
  const MODE_CONFIG_RULE_CN =
    'https://www.oceanbase.com/docs/community-obd-cn-1000000001188758';
  const MODE_CONFIG_RULE_EN =
    'https://en.oceanbase.com/docs/community-obd-en-10000000001181555';
  const MODE_CONFIG_RULE =
    getLocale() === 'zh-CN' ? MODE_CONFIG_RULE_CN : MODE_CONFIG_RULE_EN;

  //错误码文档
  const ERR_CODE_CN =
    'https://www.oceanbase.com/product/ob-deployer/error-codes';
  const ERR_CODE_EN =
    'https://en.oceanbase.com/product/ob-deployer-en/error-codes';

  const ERR_CODE = getLocale() === 'zh-CN' ? ERR_CODE_CN : ERR_CODE_EN;

  // 部署向导帮助文档
  const DOCS_PRODUCTION_CN =
    'https://www.oceanbase.com/docs/community-obd-cn-1000000001188793';
  const DOCS_PRODUCTION_EN =
    'https://en.oceanbase.com/docs/community-obd-en-10000000001181618';
  const DOCS_PRODUCTION =
    getLocale() === 'zh-CN' ? DOCS_PRODUCTION_CN : DOCS_PRODUCTION_EN;

  // SOP文档
  const DOCS_SOP = 'https://ask.oceanbase.com/t/topic/35605473';

  // OCP 发布记录
  const RELEASE_RECORD_CN = 'https://www.oceanbase.com/softwarecenter';
  const RELEASE_RECORD_EN = 'https://en.oceanbase.com/softwarecenter';
  const RELEASE_RECORD =
    getLocale() === 'zh-CN' ? RELEASE_RECORD_CN : RELEASE_RECORD_EN;

  // Grafana官网
  const DOCS_GRAFANA = 'https://grafana.com/';

  // Prometheus
  const DOCS_PROMETHEUS = 'https://prometheus.io/';

  return {
    DOCS_LINK,
    DOCS_USER,
    OFFICAIL_WEBSITE,
    FORUMS_VISITED,
    HELP_CENTER,
    OBD_DOCS,
    OCP_EXPRESS,
    OCP_DOCS,
    OBAGENT_DOCS,
    OBPROXY_DOCS,
    MODE_CONFIG_RULE,
    ERR_CODE,
    DOCS_PRODUCTION,
    DOCS_SOP,
    RELEASE_RECORD,
    OBCONFIGSERVER_DOCS,
    DOCS_GRAFANA,
    DOCS_PROMETHEUS,
  };
}
