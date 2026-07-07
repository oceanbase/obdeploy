import { useEffect, useRef, useState } from 'react';
import { Input, Tooltip } from 'antd';

interface Props {
  value?: string;
  onChange?: (value?: string) => void;
  placeholder: string;
  name: string;
  isPassword?: boolean;
  fieldProps?: any;
  id?: string;
}

export default ({
  value,
  onChange,
  placeholder,
  name,
  isPassword,
  fieldProps,
  id,
}: Props) => {
  const [visible, setVisible] = useState(false);
  const [currentValue, setCurrentValue] = useState(value);
  const open = useRef<{ input?: boolean; tooltip?: boolean }>({});

  useEffect(() => {
    setCurrentValue(value);
  }, [value]);

  const onMouseEnterInput = () => {
    open.current = {
      ...(open?.current || {}),
      input: true,
    };
    setVisible(true);
  };

  const onMouseEnterTooltip = () => {
    open.current = {
      ...(open?.current || {}),
      tooltip: true,
    };
    setVisible(true);
  };

  const onMouseLeaveInput = () => {
    setTimeout(() => {
      if (!open?.current?.tooltip) {
        setVisible(false);
      }
    }, 300);
  };

  const onMouseLeaveTooltip = () => {
    setVisible(false);
  };

  const addEventTooltipOverlay = () => {
    const tooltipOverlay = document.querySelector(
      `.tooltip-input-tooltip-overlay-${name}`,
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
    const inputConatiner = document.querySelector(`.tooltip-input-${name}`);
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
      `.tooltip-input-tooltip-overlay-${name}`,
    );
    const inputConatiner = document.querySelector(`.tooltip-input-${name}`);
    addEventTooltipOverlay();
    addEventInputConatiner();
    return () => {
      tooltipOverlay?.removeEventListener('mouseenter', onMouseEnterTooltip);
      tooltipOverlay?.removeEventListener('mouseleave', onMouseLeaveTooltip);
      inputConatiner?.removeEventListener('mouseenter', onMouseEnterInput);
      inputConatiner?.removeEventListener('mouseleave', onMouseLeaveInput);
    };
  }, []);

  const handleChange = (nextValue: string) => {
    setCurrentValue(nextValue);
    onChange?.(nextValue);
    setVisible(false);
  };

  const inputCommonProps = {
    id,
    className: `tooltip-input-${name}`,
    placeholder,
    allowClear: true,
    value: currentValue,
    onFocus: () => setVisible(false),
    ...fieldProps,
  };

  return (
    <Tooltip
      open={!currentValue && placeholder?.length > 48 && visible}
      title={placeholder}
      overlayClassName={`tooltip-input-tooltip-overlay-${name}`}
    >
      {isPassword ? (
        <Input.Password
          {...inputCommonProps}
          onChange={(e) => handleChange(e?.target?.value)}
          style={{ width: 448, ...fieldProps?.style }}
        />
      ) : (
        <Input
          {...inputCommonProps}
          onChange={(e) => handleChange(e?.target?.value)}
          autoComplete="off"
          style={{ width: 448, ...fieldProps?.style }}
        />
      )}
    </Tooltip>
  );
};
