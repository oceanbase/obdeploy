import { useState } from 'react';

import CheckInfo from './CheckInfo';
import PreCheck from './PreCheck';
import { getTailPath } from '@/utils/helper';

export default function OCPPreCheck(prop: API.StepProp) {
  const [preCheckVisible, setPreCheckVisible] = useState<boolean>(false);
  const isNewDB = getTailPath() === 'install'
  return (
    <>
      {!preCheckVisible ? (
        <CheckInfo {...prop} isNewDB={isNewDB} showNext={setPreCheckVisible} />
      ) : (
        <PreCheck isNewDB={isNewDB} {...prop} />
      )}
    </>
  );
}
