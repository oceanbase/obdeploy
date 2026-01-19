import { intl } from '@/utils/intl';
import { message, Card, Empty } from 'antd';
import { CopyOutlined } from '@ant-design/icons';
import copy from 'copy-to-clipboard';
import { getLocale } from 'umi';
import ExitPageWrapper from '@/component/ExitPageWrapper';
import { OBD_COMMAND } from '@/constant/configuration';
import EnStyles from './indexEn.less';
import ZhStyles from './indexZh.less';
import { getTailPath } from '@/utils/helper';

const locale = getLocale();
const styles = locale === 'zh-CN' ? ZhStyles : EnStyles;

export default function ExitPage() {

  const taiPath = getTailPath();
  const isUpdate = taiPath.includes('update');

  const handleCopy = () => {
    copy(OBD_COMMAND);
    message.success(
      intl.formatMessage({
        id: 'OBD.pages.components.ExitPage.CopiedSuccessfully',
        defaultMessage: '复制成功',
      }),
    );
  };

  return (
    <ExitPageWrapper target='obdeploy'>
      <Card className={styles.exitPage}>
        <Empty
          image="/assets/empty2.png"
          style={{ marginTop: '30px' }}
          description=""
        />
        <h1
          className="fw-500"
          data-aspm-click="c307511.d317289"
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.pages.components.ExitPage.ExitTheDeploymentProgramHas',
            defaultMessage: '退出-部署程序已经退出',
          })}
          data-aspm-param={``}
          data-aspm-expo
        >
          {
            isUpdate ? intl.formatMessage({
              id: 'OBD.pages.Oms.ExitPage.TheUpgradeProgramHasExited',
              defaultMessage: '升级程序已经退出！',
            }) : intl.formatMessage({
              id: 'OBD.pages.components.ExitPage.TheDeploymentProgramHasExited',
              defaultMessage: '部署程序已经退出！',
            })
          }
        </h1>
        <div
          className={styles.exitPageText}
          data-aspm-click="c307511.d317288"
          data-aspm-desc={intl.formatMessage({
            id: 'OBD.pages.components.ExitPage.ExitRestartPrompt',
            defaultMessage: '退出-再次启动提示',
          })}
          data-aspm-param={``}
          data-aspm-expo
        >
          {intl.formatMessage({
            id: 'OBD.pages.components.ExitPage.ToStartAgainGoTo',
            defaultMessage: '如需再次启动，请前往中控服务器执行',
          })}

          <a>
            {OBD_COMMAND} <CopyOutlined onClick={handleCopy} />
          </a>
        </div>
      </Card>
    </ExitPageWrapper>
  );
}
