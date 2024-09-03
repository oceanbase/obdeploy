import { useModel } from '@umijs/max';
import PreCheckInfo from './PreCheckInfo';
import PreCheckStatus from './PreCheckStatus';

export default function PreCheck() {
  const { preCheckInfoOk } = useModel('componentDeploy');
  return !preCheckInfoOk ? <PreCheckInfo /> : <PreCheckStatus />;
}
