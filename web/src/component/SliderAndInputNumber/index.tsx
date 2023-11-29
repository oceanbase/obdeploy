import React, { useState, useEffect } from 'react';
import { InputNumber, Slider, Row, Col } from '@oceanbase/design';

import styles from './index.less';

export interface SliderAndInputNumberProps {
  max: number;
  min: number;
  value?: number;
  addonAfter?: string;
  onChange?: (value: number) => void;
}

const SliderAndInputNumber: React.FC<SliderAndInputNumberProps> = ({
  max,
  min,
  value,
  addonAfter = 'GiB',
  onChange,
}) => {
  const [currentValue, setCurrentValue] = useState<number>(value || 0);

  useEffect(() => {
    if (value) {
      setCurrentValue(value);
    }
  }, [value]);

  const onHandleChange = (val: number) => {
    setCurrentValue(val);
    if (onChange) {
      onChange(val);
    }
  };

  return (
    <Row gutter={24} className={styles.SliderAndInputNumber}>
      <Col span={17}>
        <Slider
          max={max}
          min={min}
          // marks={{
          //   0: min,
          //   100: max
          // }}
          value={currentValue}
          onChange={onHandleChange}
        />
        <div className={styles.marks}>
          <div>{min}</div>
          <div>{max}</div>
        </div>
      </Col>
      <Col span={7}>
        <InputNumber
          max={max}
          min={min}
          addonAfter={addonAfter}
          value={currentValue}
          onChange={onHandleChange}
        />
      </Col>
    </Row>
  );
};

export default SliderAndInputNumber;
