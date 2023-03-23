// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/deployments/:name': (req: Request, res: Response) => {
    res
      .status(200)
      .send({
        code: 92,
        data: null,
        msg: '半质他运步己很自却力效头西效。',
        success: true,
      });
  },
};
