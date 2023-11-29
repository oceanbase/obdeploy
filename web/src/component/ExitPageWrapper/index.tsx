import { useEffect } from 'react';
import { history } from 'umi';
import { PathType } from '@/pages/type';
import { TIME_REFRESH } from '@/pages/constants';

export default function ExitPageWrapper(props: {
  target?: PathType;
  children: React.ReactNode;
}) {
  const { target } = props;
  let path: PathType | undefined;
  path = target
    ? target
    : //@ts-ignore
      (history.location.query.path as PathType | undefined);
  const PATH_HANDLES = [
    {
      paths: ['guide', 'ocpInstaller', 'update'],
      exec(path: PathType) {
        history.push(`/${path}`);
      },
    },
    {
      paths: ['configuration', 'install'],
      exec(path: PathType) {
        history.push(`/ocpinstaller/${path}`);
      },
    },
    {
      paths: ['obdeploy'],
      exec(path: PathType) {
        history.push('/');
      },
    },
  ];
  const setStorage = () => {
    if (path) {
      sessionStorage.setItem(
        'pathInfo',
        JSON.stringify({
          path,
          timestamp: new Date().getTime(),
        }),
      );
    }
  };
  const toTargetPage = (path: PathType) => {
    sessionStorage.removeItem('pathInfo');
    const targetHandler = PATH_HANDLES.find((item) =>
      item.paths.includes(path),
    );
    if (targetHandler) {
      targetHandler.exec(path);
    }
  };

  useEffect(() => {
    let sessionData;
    try {
      sessionData = JSON.parse(sessionStorage.getItem('pathInfo') as string);
    } catch (e) {
      
    } finally {
      if (sessionData) {
        const isRefresh =
          new Date().getTime() - sessionData.timestamp <= TIME_REFRESH;
        if (isRefresh) {
          toTargetPage(sessionData.path);
        }
      }
    }

    window.addEventListener('beforeunload', setStorage);
    return () => {
      window.removeEventListener('beforeunload', setStorage);
    };
  }, []);

  return <div>
    {props.children}
    </div>;
}
