import type { ImgHTMLAttributes } from 'react';
import React from 'react';

interface PrecheckedProps extends ImgHTMLAttributes<HTMLImageElement> {
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}

const Prechecked: React.FC<PrecheckedProps> = ({ size = 12, ...restProps }) => {
  return <img src="/assets/install/prechecked.svg" height={size} width={size} {...restProps} />;
};

export default Prechecked;
