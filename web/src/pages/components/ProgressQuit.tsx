import { intl } from '@/utils/intl';
import { Card, Empty } from 'antd';
import { getLocale } from 'umi';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

export default function ProgressQuit() {
  return (
    <Card className={styles.exitPage}>
      <Empty
        image="/assets/empty2.png"
        style={{ marginTop: '30px' }}
        description=""
      />

      <h1
        className="fw-500"
        data-aspm-click="c307511.d326702"
        data-aspm-desc={intl.formatMessage({
          id: 'OBD.pages.components.ProgressQuit.ExitServiceStoppedOnThe',
          defaultMessage: '退出-当前页面已停止服务',
        })}
        data-aspm-param={``}
        data-aspm-expo
      >
        {intl.formatMessage({
          id: 'OBD.pages.components.ProgressQuit.YouHaveSelectedToDeploy',
          defaultMessage: '您已选择在其他页面进行部署工作，当前页面已停止服务',
        })}
      </h1>
    </Card>
  );
}
