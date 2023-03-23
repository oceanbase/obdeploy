// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/deployments': (req: Request, res: Response) => {
    res.status(200).send({
      code: 83,
      data: { total: 64, items: [{ name: '江芳', status: 'error' }] },
      msg: '商生间提国器接他很即阶这一除号计。',
      success: true,
    });
  },
};
