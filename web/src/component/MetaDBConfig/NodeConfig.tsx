import { intl } from '@/utils/intl';
import { ProForm } from '@ant-design/pro-components';
import styles from './index.less';
import { commonInputStyle } from '@/pages/constants';
import { Select, Row } from 'antd';
import { ocpServersValidator } from '@/utils';
import { useModel } from 'umi';
import { FormInstance } from 'antd/lib/form';

export default function NodeConfig({ form }: { form: FormInstance<any> }) {
  const { isSingleOcpNode, setIsSingleOcpNode } = useModel('ocpInstallData');

  const selectChange = (value: string[]) => {
    if (isSingleOcpNode === true && value.length > 1) {
      setIsSingleOcpNode(false);
    } else if (value.length === 1) {
      setIsSingleOcpNode(true);
    } else if (value.length === 0) {
      setIsSingleOcpNode(undefined);
    }
  };

  return (
    <div>
      <p className={styles.titleText}>
        {intl.formatMessage({
          id: 'OBD.component.MetaDBConfig.NodeConfig.OcpNodeConfiguration',
          defaultMessage: 'OCP 节点配置',
        })}
      </p>

      <Row>
        <ProForm.Item
          rules={[
            {
              required: true,
              message: intl.formatMessage({
                id: 'OBD.component.MetaDBConfig.NodeConfig.PleaseEnter',
                defaultMessage: '请输入',
              }),
            },
            {
              validator: ocpServersValidator,
            },
          ]}
          label={intl.formatMessage({
            id: 'OBD.component.MetaDBConfig.NodeConfig.SelectHost',
            defaultMessage: '选择主机',
          })}
          style={{ ...commonInputStyle, marginRight: 12 }}
          name={['ocpserver', 'servers']}
        >
          <Select
            mode="tags"
            onBlur={() => form.validateFields([['ocpserver', 'servers']])}
            onChange={selectChange}
          />
        </ProForm.Item>
      </Row>
    </div>
  );
}
