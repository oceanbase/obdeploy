// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/deployments': (req: Request, res: Response) => {
    res.status(200).send({
      code: 66,
      data: {
        total: 64,
        items: [
          { name: '姚霞', status: 'processing' },
          { name: '杨静', status: 'error' },
          { name: '孔艳', status: 'error' },
          { name: '史明', status: 'error' },
          { name: '蔡杰', status: 'error' },
          { name: '毛静', status: 'default' },
          { name: '崔强', status: 'processing' },
          { name: '董超', status: 'default' },
          { name: '魏霞', status: 'error' },
          { name: '冯洋', status: 'error' },
          { name: '易强', status: 'processing' },
          { name: '曹磊', status: 'warning' },
        ],
      },
      msg: '想题准算斗子越该话代质部书太影。',
      success: true,
    });
  },
};
