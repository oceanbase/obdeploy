import type { ImgHTMLAttributes } from 'react';
import React from 'react';

interface NewIconProps extends ImgHTMLAttributes<HTMLImageElement> {
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}

const NewIcon: React.FC<NewIconProps> = ({ size = 12, ...restProps }) => {
  return <img src="/assets/icon/new.svg" height={size} width={size} {...restProps} />;
};

export default NewIcon;
