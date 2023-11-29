import React from 'react';
import { isEnglish } from '@/utils';

export interface OCPLogoProps {
  onClick?: (e: React.SyntheticEvent) => void;
  height?: number;
  mode?: 'default' | 'simple';
  style?: React.CSSProperties;
  className?: string;
}

const OCPLogo: React.FC<OCPLogoProps> = ({
  mode = 'default',
  height = mode === 'default' ? 80 : 24,
  style,
  ...restProps
}) => {
  const logoUrl = isEnglish()
    ? '/assets/logo/ocp_express_logo_en.svg'
    : '/assets/logo/ocp_express_logo_zh.svg';
  const simpleLogoUrl = isEnglish()
    ? '/assets/logo/ocp_express_simple_logo_en.svg'
    : '/assets/logo/ocp_express_simple_logo_zh.svg';
  return (
    <img
      src={mode === 'default' ? logoUrl : simpleLogoUrl}
      alt="logo"
      {...restProps}
      style={{
        height,
        ...(style || {}),
      }}
    />
  );
};

export default OCPLogo;
