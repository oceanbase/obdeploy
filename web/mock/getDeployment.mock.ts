// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/deployments': (req: Request, res: Response) => {
    res.status(200).send({
      code: 72,
      data: {
        total: 99,
        items: [
          { name: '侯娟', status: 'error' },
          { name: '郝丽', status: 'default' },
          { name: '康敏', status: 'default' },
          { name: '傅娜', status: 'default' },
          { name: '彭霞', status: 'success' },
          { name: '余娜', status: 'processing' },
          { name: '石刚', status: 'error' },
          { name: '邓伟', status: 'success' },
          { name: '许强', status: 'warning' },
          { name: '邓静', status: 'success' },
          { name: '熊平', status: 'processing' },
          { name: '任军', status: 'processing' },
          { name: '陈磊', status: 'error' },
          { name: '赖军', status: 'processing' },
          { name: '姚敏', status: 'default' },
          { name: '徐刚', status: 'processing' },
          { name: '刘秀英', status: 'processing' },
          { name: '朱涛', status: 'error' },
          { name: '潘杰', status: 'error' },
        ],
      },
      msg: '位元活做将二酸界放文习北矿的想还。',
      success: true,
    });
  },
};
