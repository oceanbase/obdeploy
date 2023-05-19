// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/deployments/:name': (req: Request, res: Response) => {
    res
      .status(200)
      .send({
        code: 67,
        data: null,
        msg: '气省组人车别传正对酸半传打反委育天。',
        success: true,
      });
  },
};
