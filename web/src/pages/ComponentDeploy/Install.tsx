import { useModel } from '@umijs/max';
import InstallProcess from './InstallProcess';
import InstallResult from './InstallResult';
export default function Install() {
  const { installFinished } = useModel('componentDeploy');
  return !installFinished ? <InstallProcess /> : <InstallResult />;
}
