import type { ImgHTMLAttributes } from 'react';
import React from 'react';

interface ClusterIconProps extends ImgHTMLAttributes<HTMLImageElement> {
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}

const ClusterIcon: React.FC<ClusterIconProps> = ({ size = 12, ...restProps }) => {
  return <img src="/assets/cluster/cluster.svg" height={size} width={size} {...restProps} />;
};

export default ClusterIcon;
