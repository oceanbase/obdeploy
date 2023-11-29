import React from 'react';
import { useToken } from '@oceanbase/design';
import type { TooltipProps } from 'antd/es/tooltip';
import { QuestionCircleOutlined } from '@ant-design/icons';
import ContentWithIcon from '@/component/ContentWithIcon';

export interface ContentWithQuestionProps {
  content?: React.ReactNode;
  /* tooltip 为空，则不展示 quertion 图标和 Tooltip */
  tooltip?: TooltipProps;
  /* 是否作为 label */
  inLabel?: boolean;
  onClick?: (e: React.SyntheticEvent) => void;
  style?: React.CSSProperties;
  className?: string;
}

const ContentWithQuestion: React.FC<ContentWithQuestionProps> = ({
  content,
  tooltip,
  inLabel,
  ...restProps
}) => {
  const { token } = useToken();
  return (
    <ContentWithIcon
      content={content}
      affixIcon={
        tooltip && {
          component: QuestionCircleOutlined,
          pointable: true,
          tooltip,
          style: {
            color: token.colorIcon,
            cursor: 'help',
            marginTop: '-4px',
          },
        }
      }
      {...restProps}
    />
  );
};

export default ContentWithQuestion;
