import { intl } from '@/utils/intl';
import React, { useState, useEffect } from 'react';
import { Dropdown, Menu } from '@oceanbase/design';
import { DownOutlined, CaretDownOutlined } from '@ant-design/icons';
import type { DropDownProps } from 'antd/es/dropdown';
import { toString } from 'lodash';
import { ALL } from '@/constant';
import ContentWithIcon from '@/component/ContentWithIcon';

type MenuItem = {
  value?: string | number;
  label?: string;
  [key: string]: any;
};

export interface MyDropdownProps extends Omit<DropDownProps, 'overlay'> {
  value?: string | number;
  // 需要设置默认值优先级使用 defaultMenuKey，使用 value 可能与 menuKey 的 useEffect 的逻辑产生意外的情况
  defaultMenuKey?: string | number;
  menuList: MenuItem[];
  showAll?: boolean;
  allLabel?: string;
  onChange?: (value: number | string) => void;
  valueProp?: string;
  style?: React.CSSProperties;
  className?: string;
  // 是否使用实心的图标
  isSolidIcon?: boolean;
}

const MyDropdown: React.FC<MyDropdownProps> = ({
  value,
  defaultMenuKey,
  menuList = [],
  showAll = false,
  allLabel,
  onChange,
  valueProp = 'value',
  style = {},
  className,
  isSolidIcon = false,
  ...restProps
}) => {
  const newMenuList = showAll
    ? [
        {
          value: ALL,
          label:
            allLabel ||
            intl.formatMessage({
              id: 'OBD.src.component.MyDropdown.All',
              defaultMessage: '全部',
            }),
        },

        ...menuList,
      ]
    : menuList;

  const firstMenuKey = newMenuList && newMenuList[0] && newMenuList[0].value;

  /**
   * 需要加上 value，不然设置了 value 未设置 defaultMenuKey 会导致值一直在 firstMenuKey 和 value 死循环
   * 因为 useEffect 里面同时对 menuKey 和 value 进行了设置，首次设置会冲突
   *  */
  const realDefaultMenuKey = defaultMenuKey || value;
  const [menuKey, setMenuKey] = useState(realDefaultMenuKey || firstMenuKey);
  // Dropdown 组件的 menuKey 是 string 类型，value 可能是非 string 类型的值，并且 menuKey 的初始化值可能不是 string 类型，统一转成 string 再做判断
  const menuItem =
    newMenuList?.find((item) => toString(item.value) === toString(menuKey)) ||
    {};

  useEffect(() => {
    if (onChange) {
      onChange(menuItem[valueProp]);
    }
  }, [menuKey]);

  useEffect(() => {
    if (value) {
      // 为了保证 Dropdown 组件的 menuKey 是 string 类型，设置时需要转成 string
      setMenuKey(toString(value));
      if (onChange) {
        onChange(value);
      }
    }
  }, [value]);

  const menu = (
    <Menu
      onClick={({ key }) => {
        setMenuKey(key as string);
      }}
    >
      {newMenuList.map((item) => (
        <Menu.Item key={item.value}>{item.label}</Menu.Item>
      ))}
    </Menu>
  );

  return (
    <Dropdown placement="bottomLeft" {...restProps} overlay={menu}>
      <ContentWithIcon
        className={`my-dropdown pointable ${className}`}
        affixIcon={{
          component: isSolidIcon ? CaretDownOutlined : DownOutlined,
        }}
        content={menuItem.label}
        style={style}
      />
    </Dropdown>
  );
};

export default MyDropdown;
