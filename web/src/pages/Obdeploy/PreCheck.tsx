import { useModel } from '@umijs/max';
import CheckInfo from './CheckInfo';
import PreCheckStatus from './PreCheckStatus';

export default function PreCheck() {
  const { checkOK } = useModel('global');

  return checkOK ? <PreCheckStatus /> : <CheckInfo />;
}
