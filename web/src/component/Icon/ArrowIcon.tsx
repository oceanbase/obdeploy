import type { ImgHTMLAttributes } from 'react';
import React from 'react';

interface ArrowIconProps extends ImgHTMLAttributes<HTMLImageElement> {
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}

const ArrowIcon: React.FC<ArrowIconProps> = ({ size = 12, ...restProps }) => {
  return <img src="/assets/update/arrow.svg" height={size} width={size} {...restProps} />;
};

export default ArrowIcon;
