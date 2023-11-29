import { ProCard } from '@ant-design/pro-components';
import type { FormInstance } from 'antd/lib/form';

import MateDBUserConfig from '../MetaDBConfig/UserConfig';
import NodeConfig from '../MetaDBConfig/NodeConfig';

export default function UserConfig({ form }: { form: FormInstance<any> }) {
  return (
    <ProCard>
      <MateDBUserConfig form={form}/>
      <NodeConfig form={form}/>
    </ProCard>
  );
}
