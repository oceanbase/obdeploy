import { message, Card } from 'antd';
import { CopyOutlined } from '@ant-design/icons';
import copy from 'copy-to-clipboard';
import styles from './index.less';

export default function ExitPage() {
  const command = 'obd web';

  const handleCopy = () => {
    copy(command);
    message.success('复制成功');
  };

  return (
    <Card className={styles.exitPage}>
      <h1
        data-aspm-click="c307511.d317289"
        data-aspm-desc="退出-部署程序已经退出"
        data-aspm-param={``}
        data-aspm-expo
      >
        部署程序已经退出！
      </h1>
      <div
        className={styles.exitPageText}
        data-aspm-click="c307511.d317288"
        data-aspm-desc="退出-再次启动提示"
        data-aspm-param={``}
        data-aspm-expo
      >
        如需再次启动，请前往中控服务器执行
        <a>
          {command} <CopyOutlined onClick={handleCopy} />
        </a>
      </div>
    </Card>
  );
}
