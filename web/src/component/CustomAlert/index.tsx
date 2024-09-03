import type { AlertProps } from 'antd';
import { Alert } from 'antd';
import styles from './index.less';
export default function CustomAlert(props: AlertProps) {
  const alertTypeClass = props.type || 'info';
  return (
    <Alert
      showIcon={true}
      {...props}
      className={`${styles.alertContainer} ${styles[`alert-${alertTypeClass}`]}`}
    />
  );
}
