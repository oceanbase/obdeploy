import { intl } from '@/utils/intl';
import { Select, Tag, Tooltip } from 'antd';
import { useEffect, useRef, useState } from 'react';

interface Props {
  value?: string[];
  onChange?: (values?: string[]) => void;
  name?: string;
  setLastDeleteServer: (value: string) => void;
  standAlone?: boolean;
  onBlur?: () => void;
}

export default ({
  value: values,
  onChange,
  name,
  standAlone,
  setLastDeleteServer,
  onBlur,
}: Props) => {
  const [visible, setVisible] = useState(false);
  const [currentValues, setCurrentValues] = useState(values);
  const getOverValues = (dataSource?: string[]) => {
    if (!dataSource || dataSource.length <= 3) {
      return [];
    }
    const copy = [...dataSource];
    return copy.splice(3);
  };

  const [overValuess, setOverValues] = useState(
    getOverValues([...(values || [])]),
  );

  const open = useRef<{ input: boolean; tooltip: boolean }>({
    input: false,
    tooltip: false,
  });

  const onMouseEnterInput = () => {
    if (open.current) {
      open.current.input = true;
    }
    setVisible(true);
  };

  const onMouseEnterTooltip = () => {
    if (open.current) {
      open.current.tooltip = true;
    }
    setVisible(true);
  };

  const onMouseLeaveInput = () => {
    setTimeout(() => {
      if (!open.current?.tooltip) {
        setVisible(false);
      }
    }, 300);
  };

  const onMouseLeaveTooltip = () => {
    setVisible(false);
  };

  const addEventTooltipOverlay = () => {
    const tooltipOverlay = document.querySelector(
      `.server-tooltip-overlay-${name}`,
    );

    if (tooltipOverlay) {
      tooltipOverlay?.addEventListener('mouseenter', onMouseEnterTooltip);
      tooltipOverlay?.addEventListener('mouseleave', onMouseLeaveTooltip);
    } else {
      setTimeout(() => {
        addEventTooltipOverlay();
      }, 500);
    }
  };

  const addEventInputConatiner = () => {
    const inputConatiner = document.querySelector(`.server-${name}`);
    if (inputConatiner) {
      inputConatiner?.addEventListener('mouseenter', onMouseEnterInput);
      inputConatiner?.addEventListener('mouseleave', onMouseLeaveInput);
    } else {
      setTimeout(() => {
        addEventInputConatiner();
      }, 500);
    }
  };

  useEffect(() => {
    const tooltipOverlay = document.querySelector(
      `.server-tooltip-overlay-${name}`,
    );

    const inputConatiner = document.querySelector(`.server-${name}`);
    addEventTooltipOverlay();
    addEventInputConatiner();
    return () => {
      tooltipOverlay?.removeEventListener('mouseenter', onMouseEnterTooltip);
      tooltipOverlay?.removeEventListener('mouseleave', onMouseLeaveTooltip);
      inputConatiner?.removeEventListener('mouseenter', onMouseEnterInput);
      inputConatiner?.removeEventListener('mouseleave', onMouseLeaveInput);
    };
  }, []);

  useEffect(() => {
    setOverValues(getOverValues([...(currentValues || [])]));
    if (onChange && currentValues?.length !== values?.length) {
      onChange(currentValues);
    }
  }, [currentValues]);

  const onSelectChange = (changeValues?: string[]) => {
    // 单机版时，输入框只允许输入一个值
    if (!changeValues) {
      setCurrentValues(undefined);
      setLastDeleteServer('');
      return;
    }
    const firstValue =
      changeValues.length > 1 ? [changeValues[0]] : changeValues;
    const value = standAlone ? firstValue : changeValues;
    setCurrentValues(value);
    setLastDeleteServer('');
  };

  const onClose = (value: string) => {
    const newCurrentValues = currentValues?.filter((item) => item !== value);
    setCurrentValues(newCurrentValues);
    setLastDeleteServer(value);
  };

  const getOverContents = () => {
    return overValuess?.map((item, index) => (
      <Tag key={`${item}-${index}`} closable onClose={() => onClose(item)}>
        {item}
      </Tag>
    ));
  };

  return (
    <Tooltip
      title={getOverContents()}
      open={overValuess && overValuess.length > 0 ? visible : false}
      overlayStyle={{ maxWidth: 400, maxHeight: 400, overflow: 'auto' }}
      overlayClassName={`server-tooltip-overlay-${name}`}
    >
      <Select
        id={`server-${name}`}
        className={`server-${name}`}
        mode="tags"
        value={currentValues}
        placeholder={standAlone ? intl.formatMessage({
          id: 'OBD.pages.Oms.ServerTags.PleaseEnterNodeIp',
          defaultMessage: '请输入节点 IP',
        }) : intl.formatMessage({
          id: 'OBD.pages.components.ServerTags.ClickEnterToEnterMultiple',
          defaultMessage: '点击回车可以输入多个节点',
        })}
        maxTagCount={3}
        allowClear
        open={false}
        onChange={onSelectChange}
        onSearch={() => setVisible(false)}
        onFocus={() => setVisible(false)}
        onBlur={() => {
          setVisible(false);
          // 调用外部传入的 onBlur 回调，触发验证
          onBlur?.();
        }}
      // onDeselect={(value) => setLastDeleteServer(value)}
      />
    </Tooltip>
  );
};
