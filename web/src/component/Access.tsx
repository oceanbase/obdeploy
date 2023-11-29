import { intl } from '@/utils/intl';
import React from 'react';
import { Button, Checkbox, Menu, Switch, Tooltip } from '@oceanbase/design';
import { isObject } from 'lodash';
import type { TooltipProps } from 'antd/es/tooltip';

export interface AccessProps {
  /* 是否可访问 */
  accessible: boolean;
  /* 所见即所得模式下，无权限时的展示内容，与 tooltip 属性是互斥的 (优先级: tooltip > fallback)，不能同时设置 */
  fallback?: React.ReactNode;
  /* 默认是所见即所得模式，如果想展示为 disabled + Tooltip 模式，则需要设置 tooltip 属性 */
  tooltip?:
    | boolean
    | (Omit<TooltipProps, 'title'> & {
        // 将 title 改为可选属性
        title?: React.ReactNode;
      });
  children: React.ReactElement;
}

export default ({
  accessible = true,
  fallback,
  tooltip = false,
  children,
  ...restProps
}: AccessProps) => {
  const childrenProps = children.props || {};
  const disabled = !accessible || childrenProps.disabled;
  const tooltipProps = isObject(tooltip) ? tooltip || {} : {};
  const { title, ...restTooltipProps } = tooltipProps;
  const element = React.cloneElement(children, {
    style: {
      // 为了保证 Tooltip -> span -> disabled Button 的组件结构下，鼠标移出按钮时 Tooltip 可以正常消失，需要设置 pointerEvents: 'none'
      // issue: https://github.com/react-component/tooltip/issues/18#issuecomment-650864750
      // 判断逻辑参考自 antd: https://github.com/ant-design/ant-design/blob/master/components/tooltip/index.tsx#L88
      ...(disabled &&
      (children.type === Button ||
        children.type === Checkbox ||
        children.type === Switch)
        ? { pointerEvents: 'none' }
        : {}),
      ...childrenProps.style,
    },
    // 从 antd 4.16.0 版本开始，Menu.Item & Menu.SubMenu 支持 HOC，只需要设置 eventKey 即可支持让 Menu.Item & Menu.SubMenu 间接嵌套在 Menu 下
    // https://github.com/ant-design/ant-design/issues/30828#issuecomment-854418007
    ...(children.type === Menu.Item || children.type === Menu.SubMenu
      ? { eventKey: children.key }
      : {}),
    ...(tooltip
      ? {
          // 根据 accessible 设置 disabled
          disabled,
        }
      : {}),
  });
  return tooltip ? (
    // disabled + Tooltip 模式
    <Tooltip
      title={
        !accessible &&
        tooltip &&
        (title ||
          intl.formatMessage({
            id: 'OBD.src.component.Access.NoOperationPermissionIsAvailable',
            defaultMessage: '暂无操作权限，请联系管理员开通权限',
          }))
      }
      {...restTooltipProps}
      {...restProps}
    >
      <span
        style={{
          ...(children.type === Button ? { display: 'inline-block' } : {}),
          // 设置 disabled 状态下鼠标的样式
          ...(disabled ? { cursor: 'not-allowed' } : {}),
        }}
      >
        {element}
      </span>
    </Tooltip>
  ) : accessible ? (
    <span
      {...restProps}
      style={{
        ...(children.type === Button ? { display: 'inline-block' } : {}),
        // 设置 disabled 状态下鼠标的样式
        ...(disabled ? { cursor: 'not-allowed' } : {}),
      }}
    >
      {element}
    </span>
  ) : (
    <>{fallback || null}</>
  );
};
