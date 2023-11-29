import { Badge, Tooltip } from '@oceanbase/design';
import React, { isValidElement } from 'react';
import classNames from 'classnames';
import Icon from '@ant-design/icons';
import type { IconComponentProps } from '@ant-design/icons/lib/components/Icon';
import type { BadgeProps } from 'antd/es/badge';
import type { TooltipProps } from 'antd/es/tooltip';
import styles from './index.less';

interface IconConfig extends IconComponentProps {
  badge?: BadgeProps;
  tooltip?: TooltipProps;
  pointable?: boolean;
}

type IconPosition = 'prefix' | 'affix';

export interface ContentWithIconProps {
  content?: React.ReactNode;
  prefixIcon?: IconConfig | React.ReactNode;
  affixIcon?: IconConfig | React.ReactNode;
  onClick?: (e: React.SyntheticEvent) => void;
  style?: React.CSSProperties;
  className?: string;
}

const ContentWithIcon: React.FC<ContentWithIconProps> = ({
  content,
  prefixIcon,
  affixIcon,
  className,
  ...restProps
}) => {
  return (
    <span className={`${styles.item} ${className}`} {...restProps}>
      {prefixIcon &&
        (isValidElement(prefixIcon) ? (
          <span className={styles.prefix}>{prefixIcon}</span>
        ) : (
          getIcon('prefix', prefixIcon)
        ))}
      <span className={styles.content}>{content}</span>
      {affixIcon &&
        (isValidElement(affixIcon) ? (
          <span className={styles.affix}>{affixIcon}</span>
        ) : (
          getIcon('affix', affixIcon)
        ))}
    </span>
  );
};

function getIcon(position: IconPosition, config: IconConfig) {
  const { component, badge, tooltip, pointable = false, ...restProps } = config;
  return (
    config && (
      <Tooltip {...tooltip} overlayStyle={{ maxWidth: 350, ...tooltip?.overlayStyle }}>
        {badge ? (
          <Badge
            {...badge}
            className={classNames(`${styles[position]}`, {
              [styles.pointable]: tooltip || pointable,
            })}
          >
            <Icon component={component} {...restProps} />
          </Badge>
        ) : (
          <span
            className={classNames(`${styles[position]}`, {
              [styles.pointable]: tooltip || pointable,
            })}
          >
            <Icon component={component} {...restProps} />
          </span>
        )}
      </Tooltip>
    )
  );
}

export default ContentWithIcon;
