import { intl } from '@/utils/intl';
import React, { createElement } from 'react';
import { Button } from '@oceanbase/design';
import styles from './index.less';

interface AobExceptionProps {
  title?: React.ReactNode;
  desc?: React.ReactNode;
  img?: string;
  actions?: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
  linkElement?: string;
  backText?: string;
  redirect?: string;
  onBack?: () => void;
}

class AobException extends React.PureComponent<AobExceptionProps> {
  constructor(props: AobExceptionProps) {
    super(props);
    this.state = {};
  }

  public render() {
    const {
      className,
      backText = intl.formatMessage({
        id: 'OBD.component.AobException.ReturnToHomePage',
        defaultMessage: '返回首页',
      }),
      title,
      desc,
      img,
      linkElement = 'a',
      actions,
      redirect = '/',
      onBack,
      ...rest
    } = this.props;

    return (
      <div className={`${styles.container} ${className}`} {...rest}>
        <div className={styles.imgWrapper}>
          <div
            className={styles.img}
            style={{ backgroundImage: `url(${img})` }}
          />
        </div>
        <div className={styles.content}>
          <h1>{title}</h1>
          <div className={styles.desc}>{desc}</div>
          <div className={styles.actions}>
            {actions ||
              (onBack ? (
                <Button type="primary" onClick={onBack}>
                  {backText}
                </Button>
              ) : (
                createElement(
                  linkElement,
                  {
                    to: redirect,
                    href: redirect,
                  },
                  <Button type="primary">{backText}</Button>,
                )
              ))}
          </div>
        </div>
      </div>
    );
  }
}

export default AobException;
