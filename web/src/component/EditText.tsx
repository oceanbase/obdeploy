import React, { useState, useEffect } from 'react';
import { Input, Row, Col } from '@oceanbase/design';
import { EditOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons';

export interface EditTextProps {
  address: string;
  onOk: (address: string) => void;
  style?: React.CSSProperties;
}

const EditText: React.FC<EditTextProps> = ({ address: initAddress, onOk, ...restProps }) => {
  const [edit, setEdit] = useState<boolean>(false);
  const [address, setAddress] = useState<string>(initAddress as string);
  const [oldAddress, setOldAddress] = useState<string>(initAddress as string);
  // 初始化默认值
  useEffect(() => {
    if (initAddress) {
      setAddress(initAddress);
      setOldAddress(initAddress);
    }
  }, [initAddress]);

  return (
    <Row gutter={[8, 0]} style={{ width: '70%' }}>
      {edit ? (
        <>
          <Col span={18}>
            <Input
              {...restProps}
              value={address}
              onChange={({ target: { value } }) => {
                setAddress(value);
              }}
            />
          </Col>
          <Col style={{ lineHeight: '32px' }}>
            <CloseOutlined
              onClick={() => {
                setAddress(oldAddress);
                setEdit(false);
              }}
            />
          </Col>
          <Col style={{ lineHeight: '32px' }}>
            <CheckOutlined
              onClick={() => {
                if (onOk) {
                  onOk(address);
                }
              }}
            />
          </Col>
        </>
      ) : (
        <>
          <Col>{address}</Col>
          <Col>
            <a>
              <EditOutlined
                onClick={() => {
                  setEdit(true);
                }}
              />
            </a>
          </Col>
        </>
      )}
    </Row>
  );
};

export default EditText;
