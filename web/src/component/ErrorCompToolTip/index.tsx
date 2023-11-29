import { Tooltip } from "antd";
import { CloseOutlined } from '@ant-design/icons';

import styles from './index.less'

interface ErrorCompToolTipProps {
    title:string,
    status:'warning' | 'error'
}

export default function ErrorCompToolTip({title,status}:ErrorCompToolTipProps) {
  return (
    <Tooltip title={title}>
      <span className={`${styles.iconContainer} ${status}-color`}>
        <CloseOutlined className={styles.icon} />
      </span>
    </Tooltip>
  );
}
