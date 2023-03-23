import { useEffect, useState, useRef } from 'react';
import { Input, Tooltip } from 'antd';

interface Props {
  value?: string;
  onChange?: (value?: string) => void;
  placeholder: string;
  name: string;
}

export default ({ value, onChange, placeholder, name }: Props) => {
  const [visible, setVisible] = useState(false);
  const [currentValue, setCurrentValue] = useState(value);
  const open = useRef();
  open.current = {
    input: false,
    tooltip: false,
  };

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
      `.dir-input-tooltip-overlay-${name}`,
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
    const inputConatiner = document.querySelector(`.dir-input-${name}`);
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
      `.dir-input-tooltip-overlay-${name}`,
    );
    const inputConatiner = document.querySelector(`.dir-input-${name}`);
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
    if (onChange) {
      onChange(currentValue);
    }
  }, [currentValue]);

  return (
    <Tooltip
      open={!currentValue && placeholder?.length > 48 && visible}
      title={placeholder}
      overlayClassName={`dir-input-tooltip-overlay-${name}`}
    >
      <Input
        className={`dir-input-${name}`}
        placeholder={placeholder}
        allowClear
        value={currentValue}
        onChange={(e: any) => {
          setCurrentValue(e?.target?.value);
          setVisible(false);
        }}
        autoComplete="off"
        style={{ width: 448 }}
        onFocus={() => setVisible(false)}
      />
    </Tooltip>
  );
};
